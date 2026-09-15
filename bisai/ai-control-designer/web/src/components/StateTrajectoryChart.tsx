import React from 'react';
import ReactECharts from 'echarts-for-react';

interface StateTrajectoryChartProps {
  time: number[];
  states: Record<string, number[]>;
  targets?: Record<string, number>;
  title?: string;
  height?: number;
  selectedStates?: string[];
}

const COLORS = ['#2563eb', '#dc2626', '#16a34a', '#d97706', '#7c3aed', '#ec4899'];

const StateTrajectoryChart: React.FC<StateTrajectoryChartProps> = ({
  time,
  states,
  targets,
  title = '状态轨迹',
  height = 300,
  selectedStates,
}) => {
  const stateKeys = selectedStates || Object.keys(states);
  const series = stateKeys.map((key, index) => {
    const data = states[key] || [];
    const color = COLORS[index % COLORS.length];
    const target = targets?.[key];

    const seriesItem: any = {
      name: key,
      type: 'line',
      data,
      smooth: true,
      lineStyle: { color, width: 2 },
      symbol: 'circle',
      symbolSize: 4,
    };

    // 如果有目标值，添加目标线
    if (target !== undefined) {
      seriesItem.markLine = {
        data: [{ yAxis: target }],
        label: { formatter: `目标: ${target}` },
        lineStyle: { color, type: 'dashed', width: 1 },
      };
    }

    return seriesItem;
  });

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
      data: stateKeys,
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
      name: '状态值',
      nameLocation: 'center',
      nameGap: 40,
    },
    series,
  };

  return <ReactECharts option={option} style={{ height }} />;
};

export default StateTrajectoryChart;