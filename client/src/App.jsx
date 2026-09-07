import React, { useState, useEffect, useRef } from "react";
import Login from "./components/Login.jsx";
import Dashboard from "./components/Dashboard.jsx";


const App = () => {
  const [email, setEmail] = useState("");
  const [loggedIn, setLoggedIn] = useState(false); // User authenticated
  const [transitioning, setTransitioning] = useState(false); // Animation running
  const [showLogin, setShowLogin] = useState(true); // Is login still rendered

  useEffect(() => {
    const token = localStorage.getItem("token");

    if (token) {
      setLoggedIn(true);
      setShowLogin(false);
    }
  }, []);

  return (
    <div className="appContainer">
      {showLogin && (
        <div className={`loginWrapper ${transitioning ? "slideUp" : ""}`}>
          <Login
            setLoggedIn={setLoggedIn}
            setTransitioning={setTransitioning}
            setShowLogin={setShowLogin}
          />
        </div>
      )}

      <div className={`dashboardWrapper ${loggedIn ? "dashboardEnter" : ""}`}>
        {loggedIn && <Dashboard 
          setLoggedIn = {setLoggedIn}
          setShowLogin={setShowLogin}
          setTransitioning={setTransitioning}
        />}
      </div>
    </div>
  );
};

export default App;
