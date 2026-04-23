import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'

type RiskLevel = 'Critical' | 'High' | 'Medium' | 'Low'
type ComplianceStatus = 'Compliant' | 'Partial' | 'Non-compliant'

interface Contract {
  id: string
  fileName: string
  vendor: string
  effectiveDate: string | null
  expiryDate: string | null
  category: string
  autoRenewal: boolean
  uploadedAt: string
}

interface ContractListItem {
  contract: Contract
  score: number
  status: ComplianceStatus
  maxRiskLevel: RiskLevel
  alerts: string[]
}

interface ClauseResult {
  name: string
  found: boolean
  quality: 'strong' | 'weak' | 'absent'
  redactedExcerpt: string
  gapDescription: string
  riskLevel: RiskLevel
}

interface Recommendation {
  clauseName: string
  priority: RiskLevel
  description: string
  suggestedText: string
}

interface Analysis {
  contractId: string
  score: number
  status: ComplianceStatus
  analyzedAt: string
  clauses: ClauseResult[]
  recommendations: Recommendation[]
  alerts: string[]
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

function App() {
  const [userId, setUserId] = useState('analyst-1')
  const [token, setToken] = useState<string>('')
  const [contracts, setContracts] = useState<ContractListItem[]>([])
  const [selectedId, setSelectedId] = useState<string>('')
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [vendorFilter, setVendorFilter] = useState<string>('')
  const [riskFilter, setRiskFilter] = useState<string>('')
  const [uploadProgress, setUploadProgress] = useState<number>(0)
  const [error, setError] = useState<string>('')

  const isAuthenticated = token.length > 0

  const selectedContract = useMemo(
    () => contracts.find((item) => item.contract.id === selectedId),
    [contracts, selectedId],
  )

  const authHeaders = (currentToken: string): HeadersInit => ({
    Authorization: `Bearer ${currentToken}`,
  })

  async function login(event: FormEvent) {
    event.preventDefault()
    setError('')
    const response = await fetch(`${API_BASE}/api/auth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ userId }),
    })
    if (!response.ok) {
      setError('Unable to authenticate')
      return
    }
    const data: { access_token: string } = await response.json()
    setToken(data.access_token)
    await refreshContracts(data.access_token)
  }

  function logout() {
    setToken('')
    setContracts([])
    setSelectedId('')
    setAnalysis(null)
    setUploadProgress(0)
    setError('')
  }

  async function refreshContracts(currentToken?: string) {
    if (!token && !currentToken) {
      return
    }
    const query = new URLSearchParams()
    if (statusFilter) {
      query.set('status_filter', statusFilter)
    }
    if (vendorFilter) {
      query.set('vendor', vendorFilter)
    }
    if (riskFilter) {
      query.set('riskLevel', riskFilter)
    }
    const url = `${API_BASE}/api/contracts${query.toString() ? `?${query.toString()}` : ''}`
    const response = await fetch(url, {
      headers: authHeaders(currentToken ?? token),
    })
    if (!response.ok) {
      setError('Failed to fetch contracts')
      return
    }
    const data: ContractListItem[] = await response.json()
    setContracts(data)
  }

  async function fetchAnalysis(contractId: string) {
    setSelectedId(contractId)
    setError('')
    const response = await fetch(`${API_BASE}/api/contracts/${contractId}/analysis`, {
      headers: authHeaders(token),
    })
    if (!response.ok) {
      setError('Failed to load analysis')
      return
    }
    const data: Analysis = await response.json()
    setAnalysis(data)
  }

  async function uploadContracts(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const input = form.elements.namedItem('contracts') as HTMLInputElement | null
    const files = input?.files
    if (!files || files.length === 0) {
      return
    }

    setError('')
    setUploadProgress(0)
    for (let index = 0; index < files.length; index += 1) {
      const formData = new FormData()
      formData.append('file', files[index])
      const upload = await fetch(`${API_BASE}/api/contracts/upload`, {
        method: 'POST',
        headers: authHeaders(token),
        body: formData,
      })
      if (!upload.ok) {
        setError('Upload failed for one or more files')
        break
      }
      setUploadProgress(Math.round(((index + 1) / files.length) * 100))
    }
    await refreshContracts()
    form.reset()
  }

  return (
    <main className="min-h-screen bg-slate-50 p-6 text-slate-800">
      <section className="mx-auto max-w-7xl space-y-6">
        <header className="rounded-lg bg-white p-4 shadow">
          <h1 className="text-2xl font-semibold">AI Contract Compliance Dashboard</h1>
          <p className="mt-1 text-sm text-slate-600">
            Sensitive text is encrypted and only redacted excerpts are used for AI analysis.
          </p>
        </header>

        {!isAuthenticated ? (
          <form className="rounded-lg bg-white p-4 shadow" onSubmit={login}>
            <label className="block text-sm font-medium text-slate-700" htmlFor="user-id">
              User ID
            </label>
            <div className="mt-2 flex gap-2">
              <input
                id="user-id"
                value={userId}
                onChange={(event) => setUserId(event.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-2"
                required
              />
              <button
                className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
                type="submit"
              >
                Login
              </button>
            </div>
          </form>
        ) : (
          <>
            <section className="grid gap-4 rounded-lg bg-white p-4 shadow md:grid-cols-2">
              <form className="space-y-3" onSubmit={uploadContracts}>
                <h2 className="text-lg font-semibold">Bulk Upload</h2>
                <input
                  className="block w-full rounded border border-slate-300 bg-white px-3 py-2"
                  name="contracts"
                  type="file"
                  accept=".pdf,.txt"
                  multiple
                  required
                />
                <button
                  className="rounded bg-emerald-600 px-4 py-2 text-white hover:bg-emerald-700"
                  type="submit"
                >
                  Upload Contracts
                </button>
                <p className="text-sm text-slate-600">Progress: {uploadProgress}%</p>
              </form>

              <div className="space-y-3">
                <h2 className="text-lg font-semibold">Filters</h2>
                <select
                  className="block w-full rounded border border-slate-300 px-3 py-2"
                  value={statusFilter}
                  onChange={(event) => setStatusFilter(event.target.value)}
                >
                  <option value="">All statuses</option>
                  <option value="Compliant">Compliant</option>
                  <option value="Partial">Partial</option>
                  <option value="Non-compliant">Non-compliant</option>
                </select>
                <input
                  placeholder="Vendor"
                  className="block w-full rounded border border-slate-300 px-3 py-2"
                  value={vendorFilter}
                  onChange={(event) => setVendorFilter(event.target.value)}
                />
                <select
                  className="block w-full rounded border border-slate-300 px-3 py-2"
                  value={riskFilter}
                  onChange={(event) => setRiskFilter(event.target.value)}
                >
                  <option value="">All risks</option>
                  <option value="Critical">Critical</option>
                  <option value="High">High</option>
                  <option value="Medium">Medium</option>
                  <option value="Low">Low</option>
                </select>
                <div className="flex gap-2">
                  <button
                    className="rounded bg-slate-800 px-3 py-2 text-white"
                    onClick={() => refreshContracts()}
                    type="button"
                  >
                    Apply Filters
                  </button>
                  <button className="rounded border px-3 py-2" onClick={logout} type="button">
                    Logout
                  </button>
                </div>
              </div>
            </section>

            <section className="grid gap-4 md:grid-cols-2">
              <div className="rounded-lg bg-white p-4 shadow">
                <h2 className="mb-3 text-lg font-semibold">Contracts</h2>
                <div className="space-y-2">
                  {contracts.map((item) => (
                    <button
                      key={item.contract.id}
                      type="button"
                      className="w-full rounded border border-slate-200 p-3 text-left hover:border-blue-400"
                      onClick={() => fetchAnalysis(item.contract.id)}
                    >
                      <div className="flex items-center justify-between">
                        <p className="font-medium">{item.contract.vendor}</p>
                        <span className="rounded px-2 py-1 text-xs font-semibold bg-slate-100">
                          {item.status}
                        </span>
                      </div>
                      <p className="text-sm text-slate-600">Score: {item.score}</p>
                      <p className="text-sm text-slate-600">
                        Expiry: {item.contract.expiryDate ?? 'Not extracted'}
                      </p>
                      <p className="text-sm text-slate-600">Max risk: {item.maxRiskLevel}</p>
                      {item.alerts.length > 0 && (
                        <ul className="mt-1 list-disc pl-5 text-xs text-amber-700">
                          {item.alerts.map((alert) => (
                            <li key={alert}>{alert}</li>
                          ))}
                        </ul>
                      )}
                    </button>
                  ))}
                  {contracts.length === 0 && (
                    <p className="text-sm text-slate-500">No contracts found for selected filters.</p>
                  )}
                </div>
              </div>

              <div className="rounded-lg bg-white p-4 shadow">
                <h2 className="mb-3 text-lg font-semibold">Detail View</h2>
                {!analysis || !selectedContract ? (
                  <p className="text-sm text-slate-500">Select a contract to see clause gaps and recommendations.</p>
                ) : (
                  <div className="space-y-4">
                    <div>
                      <p className="font-medium">{selectedContract.contract.fileName}</p>
                      <p className="text-sm text-slate-600">
                        Score {analysis.score} • {analysis.status}
                      </p>
                    </div>
                    <table className="w-full border-collapse text-sm">
                      <thead>
                        <tr className="border-b text-left">
                          <th>Clause</th>
                          <th>Quality</th>
                          <th>Risk</th>
                        </tr>
                      </thead>
                      <tbody>
                        {analysis.clauses.map((clause) => (
                          <tr key={clause.name} className="border-b align-top">
                            <td className="py-2 pr-2">
                              <p className="font-medium">{clause.name}</p>
                              <p className="text-xs text-slate-600">{clause.redactedExcerpt || 'No excerpt'}</p>
                            </td>
                            <td className="py-2 pr-2">{clause.quality}</td>
                            <td className="py-2">{clause.riskLevel}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    <div>
                      <h3 className="font-semibold">Recommendations</h3>
                      <ul className="mt-2 space-y-2 text-sm">
                        {analysis.recommendations.map((recommendation) => (
                          <li key={recommendation.clauseName} className="rounded bg-slate-50 p-2">
                            <p className="font-medium">
                              [{recommendation.priority}] {recommendation.clauseName}
                            </p>
                            <p>{recommendation.description}</p>
                            <p className="text-xs text-slate-600">{recommendation.suggestedText}</p>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}
              </div>
            </section>
          </>
        )}

        {error && <p className="rounded bg-red-100 p-3 text-sm text-red-700">{error}</p>}
      </section>
    </main>
  )
}

export default App
