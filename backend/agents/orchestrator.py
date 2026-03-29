"""
Orchestrator — runs 4 agents in parallel using LangGraph.

Key fix: uses Annotated[list, operator.add] for fields that
multiple parallel nodes write to simultaneously. This tells
LangGraph to CONCATENATE the lists instead of overwriting.
"""

import logging
import operator
import time
from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, START, END

from agents.security_agent import analyze_security
from agents.performance_agent import analyze_performance
from agents.smell_agent import analyze_smell
from agents.architecture_agent import analyze_architecture
from core.ast_parser import parse_code
from models.finding import Finding

logger = logging.getLogger(__name__)


class ReviewState(TypedDict):
    code: str
    language: str
    ast_context: str
    security_findings: list[Finding]
    performance_findings: list[Finding]
    smell_findings: list[Finding]
    architecture_findings: list[Finding]
    agents_completed: Annotated[list[str], operator.add]
    agents_failed: Annotated[list[str], operator.add]
    all_findings: list[Finding]


def prepare_state(state: ReviewState) -> dict:
    code = state["code"]
    language = state["language"]
    parse_result = parse_code(code, language)
    ast_context = parse_result.to_context_string()
    logger.info("Prepared state: %d lines, AST parsed", parse_result.total_lines)
    return {"ast_context": ast_context}


def run_security(state: ReviewState) -> dict:
    try:
        findings = analyze_security(
            code=state["code"],
            language=state["language"],
            ast_context=state.get("ast_context"),
        )
        logger.info("Security agent: %d findings", len(findings))
        return {
            "security_findings": findings,
            "agents_completed": ["security"],
        }
    except Exception as e:
        logger.error("Security agent failed: %s", str(e)[:200])
        return {
            "security_findings": [],
            "agents_failed": ["security"],
        }


def run_performance(state: ReviewState) -> dict:
    try:
        findings = analyze_performance(
            code=state["code"],
            language=state["language"],
            ast_context=state.get("ast_context"),
        )
        logger.info("Performance agent: %d findings", len(findings))
        return {
            "performance_findings": findings,
            "agents_completed": ["performance"],
        }
    except Exception as e:
        logger.error("Performance agent failed: %s", str(e)[:200])
        return {
            "performance_findings": [],
            "agents_failed": ["performance"],
        }


def run_smell(state: ReviewState) -> dict:
    try:
        findings = analyze_smell(
            code=state["code"],
            language=state["language"],
            ast_context=state.get("ast_context"),
        )
        logger.info("Smell agent: %d findings", len(findings))
        return {
            "smell_findings": findings,
            "agents_completed": ["smell"],
        }
    except Exception as e:
        logger.error("Smell agent failed: %s", str(e)[:200])
        return {
            "smell_findings": [],
            "agents_failed": ["smell"],
        }


def run_architecture(state: ReviewState) -> dict:
    try:
        findings = analyze_architecture(
            code=state["code"],
            language=state["language"],
            ast_context=state.get("ast_context"),
        )
        logger.info("Architecture agent: %d findings", len(findings))
        return {
            "architecture_findings": findings,
            "agents_completed": ["architecture"],
        }
    except Exception as e:
        logger.error("Architecture agent failed: %s", str(e)[:200])
        return {
            "architecture_findings": [],
            "agents_failed": ["architecture"],
        }


def merge_findings(state: ReviewState) -> dict:
    all_findings = (
        state.get("security_findings", [])
        + state.get("performance_findings", [])
        + state.get("smell_findings", [])
        + state.get("architecture_findings", [])
    )
    severity_order = {"P0": 0, "P1": 1, "P2": 2}
    all_findings.sort(key=lambda f: severity_order.get(f.severity.value, 99))
    logger.info(
        "Merged %d total findings from %d agents",
        len(all_findings),
        len(state.get("agents_completed", [])),
    )
    return {"all_findings": all_findings}


def _build_graph() -> StateGraph:
    graph = StateGraph(ReviewState)

    graph.add_node("prepare", prepare_state)
    graph.add_node("security", run_security)
    graph.add_node("performance", run_performance)
    graph.add_node("smell", run_smell)
    graph.add_node("architecture", run_architecture)
    graph.add_node("merge", merge_findings)

    graph.add_edge(START, "prepare")
    graph.add_edge("prepare", "security")
    graph.add_edge("prepare", "performance")
    graph.add_edge("prepare", "smell")
    graph.add_edge("prepare", "architecture")
    graph.add_edge("security", "merge")
    graph.add_edge("performance", "merge")
    graph.add_edge("smell", "merge")
    graph.add_edge("architecture", "merge")
    graph.add_edge("merge", END)

    return graph.compile()


_compiled_graph = _build_graph()


def run_review(code: str, language: str = "python") -> dict:
    start_time = time.time()

    initial_state = {
        "code": code,
        "language": language,
        "ast_context": "",
        "security_findings": [],
        "performance_findings": [],
        "smell_findings": [],
        "architecture_findings": [],
        "agents_completed": [],
        "agents_failed": [],
        "all_findings": [],
    }

    try:
        final_state = _compiled_graph.invoke(initial_state)
        elapsed = time.time() - start_time
        logger.info(
            "Review completed in %.1fs: %d findings from %d agents (%d failed)",
            elapsed,
            len(final_state.get("all_findings", [])),
            len(final_state.get("agents_completed", [])),
            len(final_state.get("agents_failed", [])),
        )
        return {
            "all_findings": final_state.get("all_findings", []),
            "agents_completed": final_state.get("agents_completed", []),
            "agents_failed": final_state.get("agents_failed", []),
        }
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error("Orchestrator failed after %.1fs: %s", elapsed, str(e)[:200])
        return {
            "all_findings": [],
            "agents_completed": [],
            "agents_failed": ["security", "performance", "smell", "architecture"],
        }
