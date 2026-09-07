import React, { useState, useEffect, useRef } from "react";
import notificationsImg from "../assets/notifications.svg";
import {
  uploadDocument,
  getDocumentCount,
  getDocuments,
} from "../api/documentApi";
import CustomPieChart from "./CustomPieChart";
import DocumentCard from "./DocumentCard";
import ProcessingStatusChart from "./ProcessingStatusChart";

const Dashboard = ({ setLoggedIn, setShowLogin, setTransitioning }) => {
  const [panelOption, setPanelOption] = useState("dashboard");
  const [searchText, setSearchText] = useState("");
  const [userBtnClick, setUserBtnClick] = useState(false);
  const [docNum, setDocNum] = useState(0);
  const [documents, setDocuments] = useState([]);
  const fileInputRef = useRef();
  const [selectedDocument, setSelectedDocument] = useState(null);

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
            className={`PanelButton ${panelOption === "analytics" ? "optionSelected" : ""}`}
            onClick={() => {
              setPanelOption("analytics");
            }}
          >
            ANALYTICS
          </button>
        </div>
      </div>
      <div className="RightPanel">
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
                        <p key={key}>
                          <strong>
                            {key.replaceAll("_", " ").toUpperCase()}:
                          </strong>{" "}
                          {value}
                        </p>
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
                <input
                  className="searchBar"
                  type="text"
                  value={searchText}
                  onChange={(e) => setSearchText(e.target.value)}
                />
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
              <div className="smallInsight">AI EXTRACTIONS TODAY</div>
              <div className="smallInsight">AVG OCR ACCURACY</div>
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
