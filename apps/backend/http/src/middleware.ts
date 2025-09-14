import type { NextFunction, Request, Response } from "express";
import jwt from "jsonwebtoken";
const JWT_SECRET = "nfrnfownjfwpjfojrfpwjfpw"

export  function authMiddleware(req: Request, res: Response, next: NextFunction): void {
    const token =req.header("authorization")
  
    if (!token) {
            res.status(401).json({ message: "Unauthorized" });
      return;
    }
  
    try {
      const decoded = jwt.verify(token, JWT_SECRET);
      //@ts-ignore
      req.userId = decoded.userId;
      next();       
    } catch (err) {
      res.status(401).json({ message: "Invalid token" });
    }
  }