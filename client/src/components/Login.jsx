import React, { useState, useEffect, useRef } from "react";
import ScanIcon from "../assets/scan-circle-outline.svg";
import AnalyticsIcon from "../assets/analytics-outline.svg";
import DocumentsIcon from "../assets/document-text-outline.svg";

const Login = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [login, setLogin] = useState("Log-in");

  return (
    <>
      <div className="login">
        <div className="loginLeft">
          <div className="LoginTopStrip">
            <div className="Logo">
              <h1 className="LogoText">FDIP</h1>
            </div>
            <div className="LogoName">
              <h1>Financial Document</h1>
              <br />
              <h1>Intelligence Platform</h1>
            </div>
          </div>
          <div className="Moto">
            <h1>INTELLIGENCE.</h1>
            <h1>AUTOMATION.</h1>
            <h1>TRUST.</h1>
          </div>
          <div className="tagline">
            <h6>
              Transform Unstructured Financial Documents Into Actionable
              Intelligence With AI
            </h6>
          </div>
          <div className="LoginIconsContainer">
            <div className="LoginIcons">
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                }}
              >
                <img src={ScanIcon} alt="Scan" />
                <h2>AI POWERED EXTRACTION</h2>
              </div>
            </div>
            <div className="LoginIcons">
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                }}
              >
                <img src={AnalyticsIcon} alt="Scan" />
                <h2>SMART ANALYTICS</h2>
              </div>
            </div>
            <div className="LoginIcons">
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                }}
              >
                <img src={DocumentsIcon} alt="Scan" />
                <h2>DOCUMENT CLASSIFICATION</h2>
              </div>
            </div>
          </div>
        </div>
        <div className="loginRight">
          <div className="LoginContainer">
            <div className="WELCOME">
              <h1>WELCOME.</h1>
            </div>
            <div className="Email">
              <h3>EMAIL ADDRESS</h3>
              <input value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div className="Password">
              <h3>PASSWORD</h3>
              <input
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            {login === "Log-in" && <button className="Login">LOG-IN</button>}
            {login === "Sign-up" && <button className="Login">SIGN-UP</button>}
            <button
              className="DontHaveAccount"
              onClick={() =>
                setLogin(login === "Log-in" ? "Sign-up" : "Log-in")
              }
            >
              DON'T HAVE AN ACCOUNT?
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default Login;
