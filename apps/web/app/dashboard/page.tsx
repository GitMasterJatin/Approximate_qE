'use client';

import React, { useState, useEffect } from 'react';
import { Settings, Play, Clock, Target, Info, Send, ArrowLeft } from 'lucide-react';
import { useSearchParams, useRouter } from 'next/navigation';

const MainDashboard: React.FC = () => {
  const searchParams = useSearchParams();
  const router = useRouter();
  const dataSource = searchParams.get('source') as 'upload' | 'existing' || 'existing';
  
  const [parameters, setParameters] = useState({
    maxRows: 1000,
    timeout: 30,
    optimization: 'balanced',
    caching: true
  });
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any>(null);
  const [explanation, setExplanation] = useState('');
  const [showExplanation, setShowExplanation] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleParameterChange = (key: string, value: any) => {
    setParameters(prev => ({ ...prev, [key]: value }));
  };

  const handleSetParameters = () => {
    // Simulate parameter setting
    alert('Parameters set successfully!');
  };

  const handleSendQuery = async () => {
    if (!query.trim()) return;
    
    setIsLoading(true);
    // Simulate query execution
    setTimeout(() => {
      setResults({
        accuracy: 99.12,
        approximateTime: ,
        actualTime: 2.1,
        rows: 156
      });
      setExplanation(
        `The query was executed successfully with high accuracy. The optimizer used index scanning for improved performance. 
        The slight difference between approximate and actual time indicates good query planning. 
        The result set contains ${Math.floor(Math.random() * 500) + 100} rows matching your criteria.`
      );
      setIsLoading(false);
    }, 2000);
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
                    value="14"
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-violet-500 focus:border-transparent"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Sample_Fraction
                  </label>
                  <input
                    value="0.3%"
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
                    value={parameters.timeout}
                    onChange={(e) => handleParameterChange('timeout', parseInt(e.target.value))}
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
                className="w-full mt-6 bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-400 hover:to-purple-500 text-white py-2 px-4 rounded-lg font-medium transition-all duration-300 shadow-lg shadow-violet-500/30"
              >
                Set Parameters
              </button>
            </div>
          </div>

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
                      <div className="text-2xl font-bold text-emerald-300">{results.accuracy}%</div>
                      <div className="text-sm text-emerald-400">Accuracy</div>
                    </div>
                    
                    <div className="bg-gradient-to-br from-cyan-500/20 to-blue-600/20 border border-cyan-500/30 rounded-lg p-4 text-center">
                      <Clock className="w-8 h-8 text-cyan-400 mx-auto mb-2" />
                      <div className="text-2xl font-bold text-cyan-300">{results.approximateTime}s</div>
                      <div className="text-sm text-cyan-400">Approx. Time</div>
                    </div>
                    
                    <div className="bg-gradient-to-br from-orange-500/20 to-red-600/20 border border-orange-500/30 rounded-lg p-4 text-center">
                      <Play className="w-8 h-8 text-orange-400 mx-auto mb-2" />
                      <div className="text-2xl font-bold text-orange-300">{results.actualTime}s</div>
                      <div className="text-sm text-orange-400">Actual Time</div>
                    </div>
                  </div>
                )}
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
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MainDashboard;
