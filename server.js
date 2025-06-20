
const express = require("express");
const cors = require("cors");
const bodyParser = require("body-parser");

const app = express();
app.use(cors());
app.use(bodyParser.json());

let passwordData = {
  password: "c2VjcmV0UGFzc3dvcmQ=", // "secretPassword" in base64
  unlockedBy: null
};

app.post("/unlock-request", (req, res) => {
  const { buyer } = req.body;
  passwordData.unlockedBy = null;
  res.json({ message: "Unlock request sent. Waiting for admin approval.", buyer });
});

app.post("/admin-approve", (req, res) => {
  const { buyer } = req.body;
  passwordData.unlockedBy = buyer;
  res.json({ message: "Password unlocked for buyer." });
});

app.post("/get-password", (req, res) => {
  const { buyer } = req.body;
  if (passwordData.unlockedBy === buyer) {
    const decodedPassword = Buffer.from(passwordData.password, 'base64').toString('utf-8');
    res.json({ password: decodedPassword });
  } else {
    res.status(403).json({ message: "Not authorized to view the password." });
  }
});

app.get("/", (req, res) => {
  res.send("Free Fire Backend Running");
});

const PORT = process.env.PORT || 4000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
