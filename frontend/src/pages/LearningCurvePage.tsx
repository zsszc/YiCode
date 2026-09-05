import { useEffect, useRef, useState } from 'react'
import { TrendingUp, BarChart3, PieChart } from 'lucide-react'

/* eslint-disable @typescript-eslint/no-explicit-any */

export default function LearningCurvePage() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const dailyRef = useRef<HTMLDivElement>(null)
  const masteryRef = useRef<HTMLDivElement>(null)
  const stageRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetch('/api/v1/evolution/learning-curve')
      .then(r => r.json())
      .then(d => {
        setData(d)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!data || typeof window === 'undefined') return

    // Load ECharts from CDN
    if (!(window as any).echarts) {
      const script = document.createElement('script')
      script.src = 'https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js'
      script.onload = () => initCharts()
      document.head.appendChild(script)
    } else {
      initCharts()
    }

    function initCharts() {
      const echarts = (window as any).echarts
      if (!echarts) return

      // Daily review chart
      if (dailyRef.current && data.daily_review?.length) {
        const chart = echarts.init(dailyRef.current)
        chart.setOption({
          title: { text: '每日复习量', left: 'center', textStyle: { fontSize: 14 } },
          tooltip: { trigger: 'axis' },
          xAxis: { type: 'category', data: data.daily_review.map((d: any) => d.date), axisLabel: { rotate: 45 } },
          yAxis: { type: 'value', name: '题数' },
          series: [{
            data: data.daily_review.map((d: any) => d.count),
            type: 'line',
            smooth: true,
            areaStyle: { opacity: 0.2 },
            itemStyle: { color: '#d97757' },
          }],
          grid: { left: 50, right: 20, top: 40, bottom: 60 },
        })
      }

      // Mastery by category chart
      if (masteryRef.current && data.mastery_by_category?.length) {
        const chart = echarts.init(masteryRef.current)
        chart.setOption({
          title: { text: '知识点掌握度（按类别）', left: 'center', textStyle: { fontSize: 14 } },
          tooltip: { trigger: 'axis', formatter: '{b}: {c}%' },
          xAxis: { type: 'category', data: data.mastery_by_category.map((d: any) => d.category) },
          yAxis: { type: 'value', max: 1, name: '掌握度' },
          series: [{
            data: data.mastery_by_category.map((d: any) => d.avg_mastery),
            type: 'bar',
            itemStyle: { color: '#4a7c59' },
            label: { show: true, formatter: '{c}%' },
          }],
          grid: { left: 50, right: 20, top: 40, bottom: 40 },
        })
      }

      // Stage distribution chart
      if (stageRef.current && data.stage_distribution?.length) {
        const chart = echarts.init(stageRef.current)
        chart.setOption({
          title: { text: '题目阶段分布', left: 'center', textStyle: { fontSize: 14 } },
          tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
          series: [{
            type: 'pie',
            radius: ['40%', '70%'],
            data: data.stage_distribution.map((d: any) => ({
              name: `阶段 ${d.stage}`,
              value: d.count,
            })),
            itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
            label: { formatter: '{b}\n{c}题', color: '#8b93a9' },
          }],
        })
      }
    }

    return () => {
      if (dailyRef.current) (window as any).echarts?.getInstanceByDom(dailyRef.current)?.dispose()
      if (masteryRef.current) (window as any).echarts?.getInstanceByDom(masteryRef.current)?.dispose()
      if (stageRef.current) (window as any).echarts?.getInstanceByDom(stageRef.current)?.dispose()
    }
  }, [data])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-journal-muted">加载中...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-4">
        <TrendingUp size={20} className="text-journal-primary" />
        <h1 className="text-xl font-bold text-journal-ink">学习曲线</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-journal-paper rounded-xl border border-journal-accentLight/50 p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 size={16} className="text-journal-primary" />
            <h2 className="font-semibold text-sm">每日复习趋势</h2>
          </div>
          <div ref={dailyRef} style={{ width: '100%', height: 280 }} />
          {(!data?.daily_review?.length) && (
            <div className="text-center text-journal-muted text-sm py-10">暂无数据</div>
          )}
        </div>

        <div className="bg-journal-paper rounded-xl border border-journal-accentLight/50 p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 size={16} className="text-journal-primary" />
            <h2 className="font-semibold text-sm">知识点掌握度</h2>
          </div>
          <div ref={masteryRef} style={{ width: '100%', height: 280 }} />
          {(!data?.mastery_by_category?.length) && (
            <div className="text-center text-journal-muted text-sm py-10">暂无数据</div>
          )}
        </div>

        <div className="bg-journal-paper rounded-xl border border-journal-accentLight/50 p-4 shadow-sm lg:col-span-2">
          <div className="flex items-center gap-2 mb-3">
            <PieChart size={16} className="text-journal-primary" />
            <h2 className="font-semibold text-sm">题目阶段分布</h2>
          </div>
          <div ref={stageRef} style={{ width: '100%', height: 320 }} />
          {(!data?.stage_distribution?.length) && (
            <div className="text-center text-journal-muted text-sm py-10">暂无数据</div>
          )}
        </div>
      </div>
    </div>
  )
}
