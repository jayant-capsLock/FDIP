import React from "react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
} from "recharts";

const ProcessingStatusChart = ({ statusCounts }) => {
  const data = [
    {
      name: "COMPLETED",
      value: statusCounts.completed,
    },
    {
      name: "PROCESSING",
      value: statusCounts.processing,
    },
    {
      name: "UPLOADED",
      value: statusCounts.uploaded,
    },
    {
      name: "PENDING",
      value: statusCounts.pending,
    },
    {
      name: "FAILED",
      value: statusCounts.failed,
    },
  ];

  const COLORS = [
    "#05fdfd",
    "#111111",
    "#888888",
    "#b4b5b5",
    "#555555",
  ];

  return (
    <div className="processingChart">

      <div className="processingChartVisual">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius="55%"
              outerRadius="82%"
              paddingAngle={3}
              stroke="#000"
              strokeWidth={2}
            >
              {data.map((entry, index) => (
                <Cell
                  key={entry.name}
                  fill={COLORS[index]}
                />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>


      <div className="processingLegend">

        {data.map((item, index) => (
          <div
            className="processingLegendItem"
            key={item.name}
          >
            <span
              className="processingLegendBox"
              style={{
                background: COLORS[index],
              }}
            ></span>

            <span className="processingLegendName">
              {item.name}
            </span>

            <strong>
              {item.value}
            </strong>
          </div>
        ))}

      </div>

    </div>
  );
};

export default ProcessingStatusChart;