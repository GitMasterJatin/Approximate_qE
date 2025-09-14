import dotenv from "dotenv";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

// resolve directory of current file
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// load .env from 3 levels up (project root)
dotenv.config({ path: join(__dirname, "../../../.env") });
export const databaseUrl = process.env.DATABASE_URL;
