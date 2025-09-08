// MongoDB initialization script
db = db.getSiblingDB("projectvis_db");

// Create a user for the application
db.createUser({
  user: "appuser",
  pwd: "apppassword",
  roles: [
    {
      role: "readWrite",
      db: "projectvis_db",
    },
  ],
});

// Insert initial data
db.messages.insertOne({
  type: "hello",
  content: "Hello World from Flask backend with MongoDB!",
  createdAt: new Date(),
});

print("Database initialized successfully!");
