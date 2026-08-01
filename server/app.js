import express from "express";
import cors from "cors";
import helmet from "helmet";
import morgan from "morgan";
import cookieParser from "cookie-parser";
import documentRoutes from "./routes/documentRoutes.js";

import authRoutes from "./routes/authRoutes.js";

const app = express();

app.use(cors());

app.use(helmet());

app.use(morgan("dev"));

app.use(express.json());

app.use(express.urlencoded({ extended: true }));

app.use(cookieParser());

app.use("/api/documents", documentRoutes);

app.get("/", (req, res) => {
    res.json({
        success: true,
        message: "Financial Document Intelligence Platform API",
    });
});

app.use("/api/auth", authRoutes);

export default app;