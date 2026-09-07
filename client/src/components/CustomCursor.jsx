import { useEffect, useState } from "react";

const CustomCursor = () => {
  const [position, setPosition] = useState({
    x: 0,
    y: 0,
  });

  const [hover, setHover] = useState(false);
  const [click, setClick] = useState(false);

  useEffect(() => {
    const moveCursor = (e) => {
      setPosition({
        x: e.clientX,
        y: e.clientY,
      });

      const target = e.target.closest(
        "button, a, .documentCard, [data-cursor]"
      );

      setHover(!!target);
    };

    const mouseDown = () => setClick(true);
    const mouseUp = () => setClick(false);

    window.addEventListener("mousemove", moveCursor);
    window.addEventListener("mousedown", mouseDown);
    window.addEventListener("mouseup", mouseUp);

    return () => {
      window.removeEventListener("mousemove", moveCursor);
      window.removeEventListener("mousedown", mouseDown);
      window.removeEventListener("mouseup", mouseUp);
    };
  }, []);

  return (
    <div
      className={`customCursor ${hover ? "hover" : ""} ${
        click ? "click" : ""
      }`}
      style={{
        left: position.x,
        top: position.y,
      }}
    >
      <svg
        viewBox="0 0 250 301"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* DARK OUTER EDGE */}

        <path
          className="cursorOutline"
          d="
            M49 31
            C48 25 53 21 59 27

            L225 150

            C238 160 239 175 226 183

            C211 190 193 190 176 194

            C159 198 151 205 142 217

            L103 267

            C94 279 77 277 71 262

            L43 78

            C41 62 42 43 49 31

            Z
          "
        />

        {/* MAIN FACE */}

        <path
          className="cursorFace"
          d="
            M52 34
            C51 30 54 28 58 31

            L221 153

            C231 161 231 170 222 176

            C208 182 191 182 174 187

            C156 191 147 199 138 211

            L99 261

            C93 269 82 268 78 257

            L50 77

            C48 62 47 45 52 34

            Z
          "
        />

        {/* SUBTLE GLASS HIGHLIGHT */}

        <path
          className="cursorHighlight"
          d="
            M56 39
            L214 157
            C219 161 218 164 214 165
            L62 53
            Z
          "
        />
      </svg>
    </div>
  );
};

export default CustomCursor;