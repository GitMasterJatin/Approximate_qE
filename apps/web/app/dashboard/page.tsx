'use client';

import React, { useState, useEffect } from 'react';
import { Settings, Play, Clock, Target, Info, Send, ArrowLeft } from 'lucide-react';
import { useSearchParams, useRouter } from 'next/navigation';

const MainDashboard: React.FC = () => {
  const searchParams = useSearchParams();
  const router = useRouter();
  const dataSource = searchParams.get('source') as 'upload' | 'existing' || 'existing';
  
  const [parameters, setParameters] = useState({
    hllPrecision: 14,
    sampleFraction: 0.3,
    tolerance: 1,
    caching: true
  });
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any>(null);
  const [explanation, setExplanation] = useState('');
  const [showExplanation, setShowExplanation] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null); // New state for status messages

  const handleParameterChange = (key: string, value: any) => {
    setParameters(prev => ({ ...prev, [key]: value }));
  };

  const handleSetParameters = async () => {
    setStatusMessage(null); // Clear previous messages
    setIsLoading(true); // Start loading
    try {
      const response = await fetch('http://127.0.0.1:5000/reload', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ error_tolerance_percent: parameters.tolerance }),
      });

      if (response.ok) {
        const data = await response.json();
        setStatusMessage(data.message || 'Parameters updated successfully!');
      } else {
        const errorData = await response.json();
        setStatusMessage(errorData.error || 'Failed to update parameters.');
      }
    } catch (error) {
      setStatusMessage('Network error or server is unreachable.');
    } finally {
      setIsLoading(false); // End loading
    }
  };

  const handleSendQuery = async () => {
    if (!query.trim()) return;
    
    setIsLoading(true);
    setStatusMessage(null); // Clear any previous status messages
    setResults(null); // Clear previous results
    setExplanation(''); // Clear previous explanation
    try {
      const response = await fetch('http://127.0.0.1:5000/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: query }),
      });

      if (response.ok) {
        const data = await response.json();
        setResults({
          accuracy: data.comparison.accuracy ? (100 - parseFloat(data.comparison.accuracy.replace('%', ''))) : null,
          approximateTime: data.approximate_result.time_sec != null ? parseFloat(data.approximate_result.time_sec) : null,
          actualTime: data.exact_result.time_sec != null ? parseFloat(data.exact_result.time_sec) : null,
          speedup_factor: data.comparison.speedup_factor ? parseFloat(data.comparison.speedup_factor.replace('x', '')) : null,
          approximateResult: data.approximate_result.result,
          exactResult: data.exact_result.result,
        });
        setExplanation(data.explanation || 'No detailed explanation available.');
        setStatusMessage('Query executed successfully.');
      } else {
        const errorData = await response.json();
        setStatusMessage(errorData.error || errorData.warning || 'Failed to execute query.');
        // If there's an approximate result even with a warning, display it
        if (errorData.approximate_response) {
          setResults((prevResults) => ({ // Use functional update to merge with existing results
            ...prevResults,
            approximateResult: errorData.approximate_response.approx_result,
            approximateTime: errorData.approximate_response.query_time_sec != null ? parseFloat(errorData.approximate_response.query_time_sec) : null,
            accuracy: null, // Clear accuracy if only approximate result is available
            actualTime: null, // Clear actual time if only approximate result is available
          }));
          setExplanation(errorData.approximate_response.explanation || 'No detailed explanation available.');
        }
      }
    } catch (error) {
      setStatusMessage('Network error or server is unreachable.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-slate-900 to-gray-900 p-4">
      <div className="max-w-7xl mx-auto">
        {/* Back Button */}
        <div className="mb-6">
          <button
            onClick={() => router.push(dataSource === 'upload' ? '/upload' : '/data-source')}
            className="flex items-center text-gray-300 hover:text-white transition-colors duration-300"
          >
            <ArrowLeft className="w-5 h-5 mr-2" />
            Back to {dataSource === 'upload' ? 'File Upload' : 'Data Source Selection'}
          </button>
        </div>

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">
            SQL Analytics Dashboard
          </h1>
          <p className="text-gray-300">
            Data Source: {dataSource === 'upload' ? 'Uploaded CSV' : 'Sample Dataset'}
          </p>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Parameters Panel */}
          <div className="lg:col-span-1 space-y-6">
            <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-6 shadow-2xl border border-gray-700">
              <div className="flex items-center mb-6">
                <div className="w-8 h-8 bg-gradient-to-br from-violet-500 to-purple-600 rounded-lg flex items-center justify-center mr-3">
                  <Settings className="w-5 h-5 text-white" />
                </div>
                <h2 className="text-xl font-semibold text-white">Fixed Engine Parameters</h2>
              </div>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    HLL Precision
                  </label>
                  <input
                    value={parameters.hllPrecision}
                    readOnly
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-violet-500 focus:border-transparent"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Sample_Fraction
                  </label>
                  <input
                    value={`${parameters.sampleFraction}%`}
                    readOnly
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-violet-500 focus:border-transparent"
                  />
                </div>
                <div className="flex items-center mb-6">
                <div className="w-8 h-8 bg-gradient-to-br from-violet-500 to-purple-600 rounded-lg flex items-center justify-center mr-3">
                  <Settings className="w-5 h-5 text-white" />
                </div>
                <h2 className="text-xl font-semibold text-white">Tuneable Engine Parameters</h2>
              </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Tolerance
                  </label>
                <input 
                    value={parameters.tolerance}
                    onChange={(e) => handleParameterChange('tolerance', parseInt(e.target.value))}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-violet-500 focus:border-transparent"/>
                </div>
                
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="caching"
                    checked={parameters.caching}
                    onChange={(e) => handleParameterChange('caching', e.target.checked)}
                    className="h-4 w-4 text-violet-600 focus:ring-violet-500 border-gray-600 rounded bg-gray-700"
                  />
                  <label htmlFor="caching" className="ml-2 block text-sm text-gray-300">
                    Enable Caching
                  </label>
                </div>
              </div>
              
              <button
                onClick={handleSetParameters}
                disabled={isLoading} // Disable when loading
                className="w-full mt-6 bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-400 hover:to-purple-500 text-white py-2 px-4 rounded-lg font-medium transition-all duration-300 shadow-lg shadow-violet-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <div className="flex items-center justify-center">
                    <svg className="animate-spin h-5 w-5 text-white mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Updating...
                  </div>
                ) : (
                  'Set Parameters'
                )}
              </button>
            </div>
          </div>
          {statusMessage && (
            <div className="mt-4 text-center text-sm font-medium text-white">
              {statusMessage}
            </div>
          )}

          {/* Main Query Area */}
          <div className="lg:col-span-2 space-y-6">
            {/* Query Input */}
            <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-6 shadow-2xl border border-gray-700">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-white">SQL Query</h2>
                <button
                  onClick={handleSendQuery}
                  disabled={isLoading || !query.trim()}
                  className="bg-gradient-to-r from-emerald-500 to-green-600 hover:from-emerald-400 hover:to-green-500 disabled:from-gray-600 disabled:to-gray-700 text-white px-6 py-2 rounded-lg font-medium flex items-center transition-all duration-300 shadow-lg shadow-emerald-500/30 disabled:shadow-none"
                >
                  <Send className="w-4 h-4 mr-2" />
                  {isLoading ? 'Executing...' : 'Send Query'}
                </button>
              </div>
              
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Enter your SQL query here..."
                className="w-full h-32 px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg font-mono text-sm text-white placeholder-gray-400 focus:ring-2 focus:ring-emerald-500 focus:border-transparent resize-none"
              />
            </div>

            {/* Results Panel */}
            {(results || isLoading) && (
              <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-6 shadow-2xl border border-gray-700">
                <h2 className="text-xl font-semibold text-white mb-4">Query Results</h2>
                
                {isLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400"></div>
                    <span className="ml-3 text-gray-300">Executing query...</span>
                  </div>
                ) : (
                  <div className="grid md:grid-cols-3 gap-4">
                    <div className="bg-gradient-to-br from-emerald-500/20 to-green-600/20 border border-emerald-500/30 rounded-lg p-4 text-center">
                      <Target className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
                      <div className="text-2xl font-bold text-emerald-300">{results.accuracy ? `${results.accuracy.toFixed(2)}%` : 'N/A'}</div>
                      <div className="text-sm text-emerald-400">Relative Avg. Accuracy</div>
                    </div>
                    
                    <div className="bg-gradient-to-br from-cyan-500/20 to-blue-600/20 border border-cyan-500/30 rounded-lg p-4 text-center">
                      <Clock className="w-8 h-8 text-cyan-400 mx-auto mb-2" />
                      <div className="text-2xl font-bold text-cyan-300">{results.approximateTime ? `${results.approximateTime.toFixed(4)}s` : 'N/A'}</div>
                      <div className="text-sm text-cyan-400">Approx. Time</div>
                    </div>
                    
                    <div className="bg-gradient-to-br from-orange-500/20 to-red-600/20 border border-orange-500/30 rounded-lg p-4 text-center">
                      <Play className="w-8 h-8 text-orange-400 mx-auto mb-2" />
                      <div className="text-2xl font-bold text-orange-300">{results.actualTime ? `${results.actualTime.toFixed(4)}s` : 'N/A'}</div>
                      <div className="text-sm text-orange-400">Actual Time</div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {results && results.speedup_factor && (
              <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-6 shadow-2xl border border-gray-700 mt-6">
                <h2 className="text-xl font-semibold text-white mb-4">Speedup Factor</h2>
                <div className="bg-gradient-to-br from-purple-500/20 to-pink-600/20 border border-purple-500/30 rounded-lg p-4 text-center">
                  <Play className="w-8 h-8 text-purple-400 mx-auto mb-2" />
                  <div className="text-2xl font-bold text-purple-300">{results.speedup_factor.toFixed(2)}x</div>
                  <div className="text-sm text-purple-400">Approximate Query Speedup</div>
                </div>
              </div>
            )}

            {/* Explanation Dialog */}
            {results && (
              <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-6 shadow-2xl border border-gray-700">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold text-white">Query Explanation</h2>
                  <button
                    onClick={() => setShowExplanation(!showExplanation)}
                    className="text-cyan-400 hover:text-cyan-300 flex items-center transition-colors duration-300"
                  >
                    <Info className="w-5 h-5 mr-1" />
                    {showExplanation ? 'Hide' : 'Show'} Details
                  </button>
                </div>
                
                {showExplanation && (
                  <div className="bg-gray-700/50 rounded-lg p-4 border border-gray-600">
                    <p className="text-gray-300 leading-relaxed">{explanation}</p>
                  </div>
                )}
                {results.approximateResult && (
                  <div className="bg-gray-700/50 rounded-lg p-4 border border-gray-600 mt-4">
                    <h3 className="text-lg font-semibold text-white mb-2">Approximate Result:</h3>
                    <pre className="text-gray-300 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(results.approximateResult, null, 2)}</pre>
                  </div>
                )}
                {results.exactResult && (
                  <div className="bg-gray-700/50 rounded-lg p-4 border border-gray-600 mt-4">
                    <h3 className="text-lg font-semibold text-white mb-2">Exact Result:</h3>
                    <pre className="text-gray-300 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(results.exactResult, null, 2)}</pre>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MainDashboard;
