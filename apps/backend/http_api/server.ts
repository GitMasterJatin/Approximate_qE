import express, { Request, Response, NextFunction } from "express";
const app = express();
const port = 3000;
app.use(express.json());

app.get("/health", (req: Request, res: Response) => {   res.json({ status: "ok" });
});


app.post

app.listen(port, () => {
  console.log(`Server is running on port ${port}`);
});


