import React from 'react';
import ReactECharts from 'echarts-for-react';

interface CostCurveChartProps {
  versions: number[];
  costs: number[];
  title?: string;
  height?: number;
  showArea?: boolean;
}

const CostCurveChart: React.FC<CostCurveChartProps> = ({
  versions,
  costs,
  title = '代价收敛曲线',
  height = 300,
  showArea = true,
}) => {
  const option = {
    title: {
      text: title,
      left: 'center',
      textStyle: { fontSize: 14, fontWeight: 500 },
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const p = params[0];
        return `版本 ${p.dataIndex + 1}<br/>代价: ${p.value.toFixed(4)}`;
      },
    },
    grid: {
      top: 50,
      bottom: 30,
      left: 60,
      right: 20,
    },
    xAxis: {
      type: 'category',
      data: versions,
      name: '版本',
      nameLocation: 'center',
      nameGap: 25,
    },
    yAxis: {
      type: 'value',
      name: '总代价',
      nameLocation: 'center',
      nameGap: 40,
      min: (value: any) => value.min - (value.max - value.min) * 0.1,
    },
    series: [
      {
        data: costs,
        type: 'line',
        smooth: true,
        lineStyle: { color: '#2563eb', width: 3 },
        symbol: 'circle',
        symbolSize: 8,
        areaStyle: showArea
          ? {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: 'rgba(37, 99, 235, 0.3)' },
                  { offset: 1, color: 'rgba(37, 99, 235, 0.05)' },
                ],
              },
            }
          : undefined,
        markPoint: {
          data: [
            {
              type: 'min',
              name: '最小值',
              symbol: 'circle',
              symbolSize: 50,
              label: { formatter: (p: any) => p.value.toFixed(2) },
            },
          ],
        },
        markLine: {
          data: [{ type: 'average', name: '平均值' }],
          label: { formatter: (p: any) => `平均: ${p.value.toFixed(2)}` },
        },
      },
    ],
  };

  return <ReactECharts option={option} style={{ height }} />;
};

export default CostCurveChart;