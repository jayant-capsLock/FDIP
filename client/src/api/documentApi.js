import axios from "axios";

const API = axios.create({
  baseURL: "http://localhost:5000/api/documents",
});

API.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

export const uploadDocument = (file) => {
  const formData = new FormData();
  formData.append("document", file);

  return API.post("/upload", formData);
};

export const getDocumentCount = () => {
  return API.get("/count");
};