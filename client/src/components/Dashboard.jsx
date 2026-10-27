import React, { useState, useEffect, useRef } from "react";
import notificationsImg from "../assets/notifications.svg";
import {
  uploadDocument,
  getDocumentCount,
  getDocuments,
  semanticSearchDocuments,
} from "../api/documentApi";
import CustomPieChart from "./CustomPieChart";
import DocumentCard from "./DocumentCard";
import ProcessingStatusChart from "./ProcessingStatusChart";
import RagChat from "./RagChat";

const Dashboard = ({ setLoggedIn, setShowLogin, setTransitioning }) => {
  const [panelOption, setPanelOption] = useState("dashboard");
  const [searchText, setSearchText] = useState("");
  const [userBtnClick, setUserBtnClick] = useState(false);
  const [docNum, setDocNum] = useState(0);
  const [documents, setDocuments] = useState([]);
  const fileInputRef = useRef();
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState(false);

  const handleLogout = () => {
    localStorage.removeItem("token");
    setLoggedIn(false);
    setShowLogin(true);
    setTransitioning(false);
  };

  const handleDrop = async (e) => {
    e.preventDefault();

    const files = Array.from(e.dataTransfer.files);

    if (files.length === 0) return;

    try {
      const res = await uploadDocument(files);
      console.log(res.data);
    } catch (err) {
      console.error(err);
      return;
    }

    const countRes = await getDocumentCount();
    setDocNum(countRes.data.count);
    const documentsRes = await getDocuments();
    setDocuments(documentsRes.data.documents);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleFileChange = async (e) => {
    const files = Array.from(e.target.files);

    if (files.length === 0) return;

    try {
      const res = await uploadDocument(files);
      console.log(res.data);
    } catch (err) {
      console.error(err);
      return;
    }

    e.target.value = "";

    const countRes = await getDocumentCount();
    setDocNum(countRes.data.count);
    const documentsRes = await getDocuments();
    setDocuments(documentsRes.data.documents);
  };

  useEffect(() => {
    const fetchDocumentCount = async () => {
      try {
        const res = await getDocumentCount();
        setDocNum(res.data.count);
      } catch (err) {
        console.error(err);
      }
    };

    const fetchDocuments = async () => {
      try {
        const res = await getDocuments();
        setDocuments(res.data.documents);
        console.log(res.data.documents);
      } catch (err) {
        console.error(err);
      }
    };

    fetchDocuments();
    fetchDocumentCount();
  }, []);

  useEffect(() => {
    const query = searchText.trim();

    if (!query) {
      setSearchResults([]);
      setSearchLoading(false);
      setSearchError(false);
      return;
    }

    let active = true;

    const timer = setTimeout(async () => {
      try {
        setSearchLoading(true);
        setSearchError(false);

        const res = await semanticSearchDocuments(query);

        if (active) {
          setSearchResults(res.data.documents || []);
        }
      } catch (err) {
        console.error("Semantic search failed:", err);

        if (active) {
          setSearchResults([]);
          setSearchError(true);
        }
      } finally {
        if (active) {
          setSearchLoading(false);
        }
      }
    }, 300);

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [searchText]);

  const renderValue = (value) => {
    if (value === null || value === undefined) return "-";

    if (Array.isArray(value)) {
      return (
        <ul>
          {value.map((item, i) => (
            <li key={i}>{renderValue(item)}</li>
          ))}
        </ul>
      );
    }

    if (typeof value === "object") {
      return (
        <ul>
          {Object.entries(value).map(([k, v]) => (
            <li key={k}>
              <strong>{k.replaceAll("_", " ")}:</strong> {renderValue(v)}
            </li>
          ))}
        </ul>
      );
    }

    return String(value);
  };

  const statusCounts = {
    processing: documents.filter((document) => document.status === "processing")
      .length,

    pending: documents.filter((document) => document.status === "pending")
      .length,

    completed: documents.filter((document) => document.status === "completed")
      .length,

    uploaded: documents.filter((document) => document.status === "uploaded")
      .length,

    failed: documents.filter((document) => document.status === "failed").length,
  };

  return (
    <div className="dashboard">
      <div className="LeftPanel">
        <div className="PanelLogo">
          <h1>FDIP</h1>
          <h3>Financial Document Intelligence Platform</h3>
        </div>
        <div className="PanelButtonWrapper">
          <button
            className={`PanelButton ${panelOption === "dashboard" ? "optionSelected" : ""}`}
            onClick={() => {
              setPanelOption("dashboard");
            }}
          >
            DASHBOARD
          </button>
          <button
            className={`PanelButton ${panelOption === "documents" ? "optionSelected" : ""}`}
            onClick={() => {
              setPanelOption("documents");
            }}
          >
            DOCUMENTS
          </button>
          <button
            className={`PanelButton ${panelOption === "rag-chat" ? "optionSelected" : ""}`}
            onClick={() => {
              setPanelOption("rag-chat");
            }}
          >
            RAG-CHAT WITH DOCUMENTS
          </button>
        </div>
      </div>
      <div className="RightPanel">
        {panelOption === "rag-chat" && <RagChat />}
        {panelOption === "documents" && (
          <div className="documentsPanel">
            {documents.map((document) => (
              <DocumentCard
                document={document}
                key={document.id}
                onClick={() => setSelectedDocument(document)}
              />
            ))}
            <div className="slidingWindow"></div>
          </div>
        )}
        {selectedDocument && (
          <>
            <div
              className="documentOverlay"
              onClick={() => setSelectedDocument(null)}
            ></div>

            <div className="documentWindow">
              <button
                className="closeDocument"
                onClick={() => setSelectedDocument(null)}
              >
                ×
              </button>

              <h1>{selectedDocument.original_filename}</h1>

              <div className="largePreview">
                {selectedDocument.mime_type.startsWith("image/") && (
                  <img
                    src={selectedDocument.preview_url}
                    alt={selectedDocument.original_filename}
                  />
                )}

                {selectedDocument.mime_type === "application/pdf" && (
                  <iframe
                    src={selectedDocument.preview_url}
                    title={selectedDocument.original_filename}
                  />
                )}
              </div>

              <div className="documentInfo">
                <p>
                  <strong>Type:</strong> {selectedDocument.document_type}
                </p>

                <p>
                  <strong>Status:</strong> {selectedDocument.status}
                </p>

                <div className="documentInfo">
                  <p>
                    <strong>TYPE:</strong> {selectedDocument.document_type}
                  </p>

                  <p>
                    <strong>STATUS:</strong> {selectedDocument.status}
                  </p>

                  {selectedDocument.metadata &&
                    Object.entries(selectedDocument.metadata).map(
                      ([key, value]) => (
                        <div key={key}>
                          <strong>
                            {key.replaceAll("_", " ").toUpperCase()}:
                          </strong>{" "}
                          {renderValue(value)}
                        </div>
                      ),
                    )}
                </div>
              </div>

              <a
                href={selectedDocument.preview_url}
                target="_blank"
                rel="noopener noreferrer"
                className="downloadDocument"
              >
                DOWNLOAD DOCUMENT
              </a>
            </div>
          </>
        )}
        {panelOption === "dashboard" && (
          <div className="mainDashboard">
            <div className="nav">
              <div className="welcomeMsg">
                <h1>DASHBOARD</h1> <h3>WELCOME</h3>{" "}
              </div>
              <div>
                <div className="searchContainer">
                  <input
                    className="searchBar"
                    type="text"
                    value={searchText}
                    onChange={(e) => setSearchText(e.target.value)}
                    placeholder="Semantic Search"
                  />

                  {searchText.trim() && (
                    <div className="searchResults">
                      {searchLoading && (
                        <div className="searchResultMessage">
                          SEARCHING DOCUMENTS...
                        </div>
                      )}

                      {!searchLoading && searchError && (
                        <div className="searchResultMessage">
                          SOMETHING WENT WRONG. TRY AGAIN.
                        </div>
                      )}

                      {!searchLoading &&
                        !searchError &&
                        searchResults.length === 0 && (
                          <div className="searchResultMessage">
                            NO MATCHING DOCUMENTS FOUND.
                          </div>
                        )}

                      {!searchLoading &&
                        !searchError &&
                        searchResults.map((document) => (
                          <div className="searchResultItem" key={document.id}>
                            <div>
                              {document.mime_type?.startsWith("image/") &&
                              document.preview_url ? (
                                <img
                                  src={document.preview_url}
                                  alt={document.original_filename}
                                />
                              ) : document.mime_type === "application/pdf" &&
                                document.preview_url ? (
                                <div
                                  style={{
                                    width: "55px",
                                    height: "65px",
                                    border: "2px solid black",
                                    background: "#d9d9d9",
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    fontWeight: "bold",
                                  }}
                                >
                                  PDF
                                </div>
                              ) : (
                                <div
                                  style={{
                                    width: "55px",
                                    height: "65px",
                                    border: "2px solid black",
                                    background: "#d9d9d9",
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                  }}
                                >
                                  DOC
                                </div>
                              )}
                            </div>

                            <div className="searchResultInfo">
                              <h3>{document.original_filename}</h3>

                              <p>TYPE: {document.document_type || "UNKNOWN"}</p>

                              <p>STATUS: {document.status}</p>

                              {document.best_matching_chunk && (
                                <p>
                                  {document.best_matching_chunk.slice(0, 100)}
                                  {document.best_matching_chunk.length > 100
                                    ? "..."
                                    : ""}
                                </p>
                              )}
                            </div>
                          </div>
                        ))}
                    </div>
                  )}
                </div>
              </div>
              <button className="NotificationButton">
                <img src={notificationsImg} alt="Notifications" />
              </button>
              <div className="userButtonWrapper">
                <button
                  className="userButton"
                  onClick={() => setUserBtnClick(!userBtnClick)}
                >
                  <div className="userIcon">
                    <h1>U</h1>
                  </div>
                  <div className="userName">
                    <h3>USER</h3>
                  </div>
                  <div className="downArrow">v</div>
                </button>
                {userBtnClick && (
                  <div className="userButtonDropDown">
                    <button onClick={handleLogout}>LOGOUT</button>
                  </div>
                )}
              </div>
            </div>
            <div className="insights">
              <div className="bigInsight">
                <div className="insightTitle">📁 TOTAL DOCUMENTS</div>
                <div className="docNum">
                  <h1>{docNum}</h1>
                </div>
              </div>
              <div className="bigInsight">
                <div className="insightTitle">DOCUMENTS BY TYPE</div>
                <div className="charts">
                  <CustomPieChart />
                </div>
              </div>
              <div className="bigInsight processingInsight">
                <div className="insightTitle">PROCESSING STATUS</div>
                <ProcessingStatusChart statusCounts={statusCounts} />
              </div>
            </div>
            <div className="midRegion">
              <div
                className="uploadDoc"
                onClick={() => fileInputRef.current.click()}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
              >
                <h1>+</h1>
                <input
                  type="file"
                  multiple
                  webkitdirectory=""
                  directory=""
                  hidden
                  ref={fileInputRef}
                  onChange={handleFileChange}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
