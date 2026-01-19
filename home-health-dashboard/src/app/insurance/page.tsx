'use client'

import { useEffect, useState } from 'react'
import { Activity } from 'lucide-react'

export default function InsurancePage() {
  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Insurance Performance</h1>
        <p className="text-gray-600 mt-2">
          Payer-specific collection metrics and payment analysis
        </p>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <Activity className="h-16 w-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Insurance Performance Coming Soon</h3>
            <p className="text-gray-600">
              This page will show detailed insurance payer performance and collection metrics.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}