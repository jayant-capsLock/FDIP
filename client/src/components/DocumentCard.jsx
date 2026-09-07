import { useEffect, useState, useRef } from "react";

const DocumentCard = ({ document, onClick }) => {
  return (
    <div className="documentCard" onClick={onClick}>

      <div className="docImgContainer">
        {document.mime_type.startsWith("image/") && (
          <img
            src={document.preview_url}
            alt={document.original_filename}
          />
        )}
      </div>

      <div className="docPreview">
        <h2>{document.original_filename}</h2>
        <p>{document.document_type}</p>
      </div>

    </div>
  );
};

export default DocumentCard;