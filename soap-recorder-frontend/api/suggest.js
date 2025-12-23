// Vercel Serverless Function - Proxy for /suggest endpoint
const BACKEND_URL = process.env.BACKEND_URL || 'http://145.79.13.137:5001';

async function handler(req, res) {
  // Set CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { word } = req.query;
    
    if (!word) {
      return res.status(400).json({ error: 'Missing word parameter' });
    }

    const response = await fetch(`${BACKEND_URL}/suggest?word=${encodeURIComponent(word)}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Backend error:', errorText);
      return res.status(response.status).json({ error: 'Suggestion fetch failed', details: errorText });
    }

    const data = await response.json();
    return res.status(200).json(data);
  } catch (error) {
    console.error('Proxy error:', error);
    return res.status(500).json({ error: 'Internal server error', message: error.message });
  }
}

module.exports = handler;
