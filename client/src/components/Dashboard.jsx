import React, { useState, useEffect, useRef } from "react";
import notificationsImg from "../assets/notifications.svg";
import { uploadDocument, getDocumentCount } from "../api/documentApi";

const Dashboard = ({ setLoggedIn, setShowLogin, setTransitioning }) => {
  const [panelOption, setPanelOption] = useState("dashboard");
  const [searchText, setSearchText] = useState("");
  const [userBtnClick, setUserBtnClick] = useState(false);
  const [docNum, setDocNum] = useState(0);
  const fileInputRef = useRef();

  const handleLogout = () => {
    localStorage.removeItem("token");
    setLoggedIn(false);
    setShowLogin(true);
    setTransitioning(false);
  };

  const handleDrop = async (e) => {
    e.preventDefault();

    const file = e.dataTransfer.files[0];

    if (!file) return;

    try {
      const res = await uploadDocument(file);
      console.log(res.data);
    } catch (err) {
      console.error(err);
    }

    const countRes = await getDocumentCount();
    setDocNum(countRes.data.count);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleFileChange = async (e) => {
    const file = e.target.files[0];

    if (!file) return;

    try {
      const res = await uploadDocument(file);
      console.log(res.data);
    } catch (err) {
      console.error(err);
    }
    e.target.value = "";

    const countRes = await getDocumentCount();
    setDocNum(countRes.data.count);
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

    fetchDocumentCount();
  }, []);

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
              <div className="bigInsight">DOCUMENTS BY TYPE</div>
              <div className="bigInsight">PROCESSING STATUS</div>
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
