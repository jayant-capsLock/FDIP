import React, { useState, useEffect, useRef } from "react";
import notificationsImg from "../assets/notifications.svg";

const Dashboard = () => {
  const [panelOption, setPanelOption] = useState("dashboard");
  const [searchText, setSearchText] = useState("");

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
              <button className="userButton">
                <div className="userIcon"><h1>U</h1></div>
                <div className="userName"><h3>USER</h3></div>
                <div className="downArrow">v</div>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
