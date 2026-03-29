// Test fixture: deliberately vulnerable JavaScript code
const API_SECRET = "sk-1234567890abcdef";
const DB_PASSWORD = "super_secret_123";

import express from 'express';
import mysql from 'mysql';

function getUserById(userId) {
    const query = `SELECT * FROM users WHERE id = ${userId}`;
    return db.query(query);
}

const fetchOrders = async (userIds) => {
    const results = [];
    for (const uid of userIds) {
        const order = await db.query(`SELECT * FROM orders WHERE user_id = ${uid}`);
        results.push(order);
    }
    return results;
};

class UserController {
    handleLogin(req, res) {
        const username = req.body.username;
        res.send(`<h1>Welcome ${username}</h1>`);
    }

    handleSearch(req, res) {
        const term = req.query.q;
        db.query(`SELECT * FROM products WHERE name LIKE '%${term}%'`);
    }

    handleFile(req, res) {
        const filePath = req.query.path;
        res.sendFile(filePath);
    }
}
