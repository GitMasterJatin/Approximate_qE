import express from "express";
import prismaClient from "@repo/db";
import type { Application, Request, Response, NextFunction } from "express";
import jwt from "jsonwebtoken";
import cors from "cors";
const JWT_SECRET = "nfrnfownjfwpjfojrfpwjfpw"


const app: Application = express();
const port = 3001;

app.use(express.json());
app.use(cors())
app.get("/health", (req: Request, res: Response) => {
  res.json({ status: "ok" });
});

app.post("/signup", async (req: Request, res: Response) => {
  const { email, password, name } = req.body;
  if (!email || !password || !name || !email.includes("@") || password.length < 8) {
    return res.status(400).json({ error: "Missing required fields" });
  }

  const existingUser = await prismaClient.user.findUnique({
    where: { email: email },
  });
  if (existingUser) {
    return res.status(400).json({ error: "User already exists" });
  }

  const user = await prismaClient.user.create({
    data: { email: email, password: password, name: name,requests:0 },
    });
  if (!user) {
    return res.status(400).json({ error: "Failed to create user" });
  }
  res.json(user);
});

app.post("/signin", async (req: Request, res: Response) => {
  const { email, password } = req.body;
  if (!email || !password || !email.includes("@") || password.length < 8) {
    return res.status(400).json({ error: "Missing required fields" });
  }

  const user = await prismaClient.user.findUnique({
    where: { email: email },
  });
  if (!user) {
    return res.status(400).json({ error: "User not found" });
  }
  if (user.password !== password) {
    return res.status(400).json({ error: "Invalid password" });
  }
  const token = jwt.sign({ userId: user.id }, JWT_SECRET);
  res.json({ token });
});




app.listen(port, () => {
    console.log(`Server is running on port ${port}`);
});

