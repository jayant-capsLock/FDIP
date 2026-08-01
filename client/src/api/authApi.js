import api from "./axios";

// Register
export const register = (userData) => {
    return api.post("/auth/register", userData);
};

// Login
export const login = (credentials) => {
    return api.post("/auth/login", credentials);
};

// Current User
export const getCurrentUser = (token) =>
    api.get("/auth/me", {
        headers: {
            Authorization: `Bearer ${token}`,
        },
    });