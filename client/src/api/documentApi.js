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

export const uploadDocument = (files) => {
  const formData = new FormData();

  files.forEach((file) => {
    formData.append("document", file);
  });

  return API.post("/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
};

export const getDocumentCount = () => {
  return API.get("/count");
};

export const getDocumentCountWithType = () => {
  return API.get("/countType");
};

export const getDocuments = () => {
  return API.get("/");
};