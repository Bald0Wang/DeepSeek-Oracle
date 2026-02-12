import { MouseEvent, useId, useMemo, useState } from "react";

import type { LifeKlineYearPoint } from "../types";

interface LifeKlineChartProps {
  points: LifeKlineYearPoint[];
  bestYears?: number[];
  worstYears?: number[];
}

const WIDTH = 960;
const HEIGHT = 280;
const PAD_LEFT = 44;
const PAD_RIGHT = 18;
const PAD_TOP = 14;
const PAD_BOTTOM = 32;

function sortPoints(points: LifeKlineYearPoint[]) {
  return [...points].sort((a, b) => a.age - b.age);
}

export function LifeKlineChart({ points, bestYears = [], worstYears = [] }: LifeKlineChartProps) {
  const gradientId = useId();
  const safePoints = useMemo(() => sortPoints(points), [points]);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  if (safePoints.length === 0) {
    return null;
  }

  const minAge = safePoints[0].age;
  const maxAge = safePoints[safePoints.length - 1].age;
  const plotWidth = WIDTH - PAD_LEFT - PAD_RIGHT;
  const plotHeight = HEIGHT - PAD_TOP - PAD_BOTTOM;
  const ageSpan = Math.max(maxAge - minAge, 1);

  const x = (age: number) => PAD_LEFT + ((age - minAge) / ageSpan) * plotWidth;
  const y = (score: number) => PAD_TOP + ((100 - score) / 100) * plotHeight;

  const plottedPoints = safePoints.map((item) => ({
    ...item,
    cx: x(item.age),
    cy: y(item.score),
  }));

  const linePath = plottedPoints
    .map((item, index) => `${index === 0 ? "M" : "L"} ${item.cx.toFixed(2)} ${item.cy.toFixed(2)}`)
    .join(" ");

  const areaPath = `${linePath} L ${x(maxAge).toFixed(2)} ${(HEIGHT - PAD_BOTTOM).toFixed(2)} L ${x(minAge).toFixed(2)} ${(HEIGHT - PAD_BOTTOM).toFixed(2)} Z`;

  const yTicks = [20, 40, 60, 80, 100];
  const hoveredPoint = hoveredIndex !== null ? plottedPoints[hoveredIndex] : null;

  const updateHoverByMouse = (event: MouseEvent<SVGSVGElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    if (!bounds.width) {
      return;
    }
    const normalizedX = (event.clientX - bounds.left) / bounds.width;
    const svgX = normalizedX * WIDTH;
    let nearest = 0;
    let nearestDist = Math.abs(plottedPoints[0].cx - svgX);
    for (let index = 1; index < plottedPoints.length; index += 1) {
      const dist = Math.abs(plottedPoints[index].cx - svgX);
      if (dist < nearestDist) {
        nearest = index;
        nearestDist = dist;
      }
    }
    setHoveredIndex(nearest);
  };

  const tooltipAlignRight = hoveredPoint ? hoveredPoint.cx > WIDTH * 0.72 : false;
  const tooltipTop = hoveredPoint
    ? Math.max(12, Math.min(74, (hoveredPoint.cy / HEIGHT) * 100 - 12))
    : 12;

  return (
    <div className="kline-chart" role="img" aria-label="人生K线分数趋势图">
      <svg
        className="kline-chart__svg"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        preserveAspectRatio="none"
        onMouseMove={updateHoverByMouse}
        onMouseLeave={() => setHoveredIndex(null)}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(215, 162, 100, 0.44)" />
            <stop offset="100%" stopColor="rgba(215, 162, 100, 0.03)" />
          </linearGradient>
        </defs>

        {yTicks.map((tick) => (
          <g key={tick}>
            <line
              className="kline-chart__grid-line"
              x1={PAD_LEFT}
              y1={y(tick)}
              x2={WIDTH - PAD_RIGHT}
              y2={y(tick)}
            />
            <text className="kline-chart__tick" x={PAD_LEFT - 8} y={y(tick) + 4}>
              {tick}
            </text>
          </g>
        ))}

        <line
          className="kline-chart__axis"
          x1={PAD_LEFT}
          y1={HEIGHT - PAD_BOTTOM}
          x2={WIDTH - PAD_RIGHT}
          y2={HEIGHT - PAD_BOTTOM}
        />

        <path d={areaPath} fill={`url(#${gradientId})`} />
        <path d={linePath} className="kline-chart__line" />
        {hoveredPoint ? (
          <line
            className="kline-chart__cursor"
            x1={hoveredPoint.cx}
            y1={PAD_TOP}
            x2={hoveredPoint.cx}
            y2={HEIGHT - PAD_BOTTOM}
          />
        ) : null}

        {plottedPoints.map((item, index) => {
          const isBest = bestYears.includes(item.age);
          const isWorst = worstYears.includes(item.age);
          const isActive = hoveredIndex === index;
          const dotRadius = isActive ? 5.6 : isBest || isWorst ? 4.5 : 3.2;
          return (
            <g key={`${item.age}-${item.year}`}>
              <circle
                cx={item.cx}
                cy={item.cy}
                r={dotRadius}
                className={`kline-chart__dot${isBest ? " kline-chart__dot--best" : ""}${isWorst ? " kline-chart__dot--worst" : ""}${isActive ? " kline-chart__dot--active" : ""}`}
                onMouseEnter={() => setHoveredIndex(index)}
              >
                <title>{`${item.age}岁｜评分${item.score}｜${item.summary}｜${item.daYun}`}</title>
              </circle>
              {item.age % 10 === 1 || item.age === maxAge ? (
                <text className="kline-chart__age" x={item.cx} y={HEIGHT - PAD_BOTTOM + 16}>
                  {item.age}
                </text>
              ) : null}
            </g>
          );
        })}
      </svg>
      {hoveredPoint ? (
        <div
          className={`kline-chart__tooltip${tooltipAlignRight ? " kline-chart__tooltip--right" : ""}`}
          style={{
            left: `${(hoveredPoint.cx / WIDTH) * 100}%`,
            top: `${tooltipTop}%`,
          }}
        >
          <p className="kline-chart__tooltip-title">{hoveredPoint.age}岁 · {hoveredPoint.year}年 · {hoveredPoint.yearGanZhi}</p>
          <p className="kline-chart__tooltip-text">评分：{hoveredPoint.score}（{hoveredPoint.summary}）</p>
          <p className="kline-chart__tooltip-text">大运：{hoveredPoint.daYun}</p>
          {hoveredPoint.focus ? <p className="kline-chart__tooltip-text">重点：{hoveredPoint.focus}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
