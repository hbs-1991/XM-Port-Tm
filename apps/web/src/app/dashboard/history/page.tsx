import JobHistory from '@/components/dashboard/JobHistory'

export default function HistoryPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Processing History</h1>
        <p className="mt-1 text-sm text-gray-500">View all your processing jobs</p>
      </div>
      
      <JobHistory />
    </div>
  )
}