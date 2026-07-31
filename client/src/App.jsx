import React, { useState, useEffect, useRef } from "react";
import Login from "./components/Login.jsx"
import Dashboard from "./components/Dashboard.jsx";

const App = () => {
  const [email, setEmail] = useState("");
  
  return (
    <>
    {/*<Login 
      email = {email}
      setEmail = {setEmail}
      />*/}
    <Dashboard/>
    </>
  )
}

export default App