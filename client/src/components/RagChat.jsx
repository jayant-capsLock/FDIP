import React, { useState } from "react";
import { askDocumentQuestion } from "../api/documentApi";

const RagChat = () => {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSend = async (e) => {
    e.preventDefault();

    if (!question.trim() || loading) {
      return;
    }

    const userQuestion = question.trim();

    // Show the user's message immediately
    setMessages((previousMessages) => [
      ...previousMessages,
      {
        role: "user",
        content: userQuestion,
      },
    ]);

    setQuestion("");
    setLoading(true);

    try {
      // Send the question to our backend
      const response = await askDocumentQuestion(userQuestion);

      const data = response.data;

      // Add the AI response to the chat
      setMessages((previousMessages) => [
        ...previousMessages,
        {
          role: "assistant",
          content: data.answer,
          sources: data.sources || [],
        },
      ]);
    } catch (error) {
      console.error("Chat error:", error);

      setMessages((previousMessages) => [
        ...previousMessages,
        {
          role: "assistant",
          content: "Something went wrong. Please try again.",
          sources: [],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rag-chat">
      <div className="rag-chat-header">
        <h2>Chat with your documents</h2>
        <p>Ask questions and get answers from your uploaded financial documents.</p>
      </div>

      <div className="rag-chat-messages">
        {messages.length === 0 && (
          <div className="rag-chat-empty">
            <h3>What would you like to know?</h3>
            <p>Ask something about your uploaded documents.</p>
          </div>
        )}

        {messages.map((message, index) => (
          <div
            key={index}
            className={`rag-message ${message.role}`}
          >
            <div className="rag-message-content">
              {message.content}
            </div>

            {message.sources && message.sources.length > 0 && (
              <div className="rag-sources">
                <p>Sources:</p>

                {message.sources.map((source, sourceIndex) => (
                  <div key={sourceIndex} className="rag-source">
                    <strong>[SOURCE {source.source_number}]</strong>
                    <span>{source.document_name}</span>
                    <span>
                      Page: {source.page_start || "Unknown"}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="rag-message assistant">
            Thinking...
          </div>
        )}
      </div>

      <form className="rag-chat-input" onSubmit={handleSend}>
        <input
          type="text"
          placeholder="Ask a question about your documents..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          disabled={loading}
        />

        <button type="submit" disabled={loading || !question.trim()}>
          Send
        </button>
      </form>
    </div>
  );
};

export default RagChat;