import { useEffect, useState } from "react";
import { getDocumentCountWithType } from "../api/documentApi";
import { Pie, PieChart, Sector, Tooltip } from "recharts";

// --------------------------------------------------
// Brutalist palette
// --------------------------------------------------

const documentColors = {
  bank_statement: "#00F5FF", // electric cyan
  invoice: "#F5F5F5",        // off-white
  payslip: "#8A8A8A",        // concrete gray
  tax_document: "#C4C4C4",   // light concrete
  receipt: "#242424",        // black/charcoal
};

// --------------------------------------------------
// Format document names
// bank_statement -> Bank Statement
// --------------------------------------------------

const formatDocumentType = (name) => {
  if (!name) return "";

  return name
    .split("_")
    .map(
      (word) =>
        word.charAt(0).toUpperCase() + word.slice(1)
    )
    .join(" ");
};

// --------------------------------------------------
// Active shape
// --------------------------------------------------

const renderActiveShape = ({
  cx,
  cy,
  midAngle,
  innerRadius,
  outerRadius,
  startAngle,
  endAngle,
  fill,
  payload,
  percent,
}) => {
  const RADIAN = Math.PI / 180;

  const sin = Math.sin(-RADIAN * (midAngle ?? 1));
  const cos = Math.cos(-RADIAN * (midAngle ?? 1));

  // Short connector
  const sx =
    (cx ?? 0) + ((outerRadius ?? 0) + 3) * cos;

  const sy =
    (cy ?? 0) + ((outerRadius ?? 0) + 3) * sin;

  const mx =
    (cx ?? 0) + ((outerRadius ?? 0) + 13) * cos;

  const my =
    (cy ?? 0) + ((outerRadius ?? 0) + 13) * sin;

  // Short horizontal section
  const ex =
    mx + (cos >= 0 ? 1 : -1) * 18;

  const ey = my;

  const textAnchor =
    cos >= 0 ? "start" : "end";

  const documentName = formatDocumentType(
    payload?.name
  );

  const percentage =
    ((percent ?? 0) * 100).toFixed(1);

  return (
    <g>
      {/* =========================================
          Active slice
          ========================================= */}
      <Sector
        cx={cx}
        cy={cy}
        innerRadius={innerRadius}
        outerRadius={outerRadius}
        startAngle={startAngle}
        endAngle={endAngle}
        fill={fill}
      />

      {/* =========================================
          Active highlight
          ========================================= */}
      <Sector
        cx={cx}
        cy={cy}
        startAngle={startAngle}
        endAngle={endAngle}
        innerRadius={(outerRadius ?? 0) + 4}
        outerRadius={(outerRadius ?? 0) + 8}
        fill={fill}
      />

      {/* =========================================
          Connector
          ========================================= */}
      <path
        d={`M${sx},${sy}L${mx},${my}L${ex},${ey}`}
        stroke={fill}
        strokeWidth={1.5}
        fill="none"
      />

      {/* Connector dot */}
      <circle
        cx={ex}
        cy={ey}
        r={2}
        fill={fill}
        stroke="none"
      />

      {/* =========================================
          Document name
          ========================================= */}
      <text
        x={ex + (cos >= 0 ? 1 : -1) * 6}
        y={ey - 3}
        textAnchor={textAnchor}
        fill="#FFFFFF"
        fontFamily="IBM Plex Mono, monospace"
        fontSize="9"
        fontWeight="600"
        letterSpacing="0.2px"
      >
        {documentName}
      </text>

      {/* =========================================
          Percentage
          ========================================= */}
      <text
        x={ex + (cos >= 0 ? 1 : -1) * 6}
        y={ey + 11}
        textAnchor={textAnchor}
        fill="#BEBEBE"
        fontFamily="IBM Plex Mono, monospace"
        fontSize="8"
        fontWeight="400"
      >
        {`${percentage}%`}
      </text>
    </g>
  );
};

// --------------------------------------------------
// Main component
// --------------------------------------------------

export default function CustomPieChart({
  isAnimationActive = true,
  defaultIndex,
}) {
  const [data, setData] = useState([]);

  // ------------------------------------------------
  // Fetch document counts
  // ------------------------------------------------

  useEffect(() => {
    const fetchDocumentCountWithType = async () => {
      try {
        const res = await getDocumentCountWithType();

        const newData = res.data.map((item) => {
          return {
            name: item.document_type,
            value: Number(item.document_count),

            fill:
              documentColors[item.document_type] ||
              "#777777",
          };
        });

        setData(newData);
      } catch (err) {
        console.error(err);
      }
    };

    fetchDocumentCountWithType();
  }, []);

  // ------------------------------------------------
  // Chart
  // ------------------------------------------------

  return (
    <PieChart
      style={{
        width: "100%",
        height: "100%",
        maxWidth: "100%",
        maxHeight: "100%",
        aspectRatio: 1,
      }}
      responsive
      margin={{
        top: 20,
        right: 35,
        bottom: 20,
        left: 35,
      }}
    >
      <Pie
        data={data}
        cx="50%"
        cy="50%"
        innerRadius="55%"
        outerRadius="67%"
        dataKey="value"
        nameKey="name"
        fill="#888888"
        isAnimationActive={isAnimationActive}
        activeShape={renderActiveShape}
      />

      <Tooltip
        content={() => null}
        defaultIndex={defaultIndex}
      />
    </PieChart>
  );
}