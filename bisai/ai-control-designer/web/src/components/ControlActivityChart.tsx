import React from 'react';
import ReactECharts from 'echarts-for-react';

interface ControlActivityChartProps {
  time: number[];
  controls: Record<string, number[]>;
  title?: string;
  height?: number;
}

const COLORS = ['#2563eb', '#dc2626', '#16a34a', '#d97706', '#7c3aed', '#ec4899'];

const ControlActivityChart: React.FC<ControlActivityChartProps> = ({
  time,
  controls,
  title = '控制活动',
  height = 300,
}) => {
  const controlKeys = Object.keys(controls);

  const series = controlKeys.map((key, index) => ({
    name: key,
    type: 'line',
    data: controls[key] || [],
    smooth: true,
    lineStyle: { color: COLORS[index % COLORS.length], width: 2 },
    symbol: 'circle',
    symbolSize: 3,
    areaStyle: {
      color: {
        type: 'linear',
        x: 0,
        y: 0,
        x2: 0,
        y2: 1,
        colorStops: [
          { offset: 0, color: `${COLORS[index % COLORS.length]}40` },
          { offset: 1, color: `${COLORS[index % COLORS.length]}10` },
        ],
      },
    },
  }));

  const option = {
    title: {
      text: title,
      left: 'center',
      textStyle: { fontSize: 14, fontWeight: 500 },
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        let html = `时间: ${params[0].axisValue}<br/>`;
        params.forEach((p: any) => {
          html += `${p.seriesName}: ${p.value.toFixed(3)}<br/>`;
        });
        return html;
      },
    },
    legend: {
      data: controlKeys,
      bottom: 0,
      icon: 'circle',
      itemWidth: 8,
      itemHeight: 8,
    },
    grid: {
      top: 50,
      bottom: 50,
      left: 50,
      right: 20,
    },
    xAxis: {
      type: 'category',
      data: time,
      name: '时间',
      nameLocation: 'center',
      nameGap: 25,
    },
    yAxis: {
      type: 'value',
      name: '控制量',
      nameLocation: 'center',
      nameGap: 40,
      min: 0,
    },
    series,
  };

  return <ReactECharts option={option} style={{ height }} />;
};

export default ControlActivityChart;