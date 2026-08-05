import axios from "axios";
import FormData from "form-data";

export const extractText = async (
  fileBuffer,
  originalFilename,
  mimeType
) => {
  const form = new FormData();

  form.append("file", fileBuffer, {
    filename: originalFilename,
    contentType: mimeType,
  });

  const { data } = await axios.post(
    "http://localhost:8000/extract",
    form,
    {
      headers: form.getHeaders(),
    }
  );

  return data.text;
};