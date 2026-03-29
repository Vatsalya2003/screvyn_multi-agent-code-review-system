import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;

public class UserService {
    private static final String DB_PASSWORD = "super_secret_123";
    
    public ResultSet getUser(String userId) throws Exception {
        Connection conn = DriverManager.getConnection("jdbc:mysql://localhost/db", "root", DB_PASSWORD);
        Statement stmt = conn.createStatement();
        return stmt.executeQuery("SELECT * FROM users WHERE id = " + userId);
    }

    public void deleteUser(String userId) throws Exception {
        Connection conn = DriverManager.getConnection("jdbc:mysql://localhost/db", "root", DB_PASSWORD);
        Statement stmt = conn.createStatement();
        stmt.execute("DELETE FROM users WHERE id = " + userId);
    }

    public void processPayment(double amount) {
        if (amount > 1000) {
            applyDiscount(amount, 0.15);
        }
    }

    private void applyDiscount(double amount, double rate) {
        double discounted = amount * rate;
    }
}
