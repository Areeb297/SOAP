// Vercel Serverless Function - Proxy for /transcribe endpoint
const BACKEND_URL = process.env.BACKEND_URL || 'http://145.79.13.137:5001';

async function handler(req, res) {
  // Set CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Collect the raw body as a buffer
    const chunks = [];
    for await (const chunk of req) {
      chunks.push(chunk);
    }
    const body = Buffer.concat(chunks);

    // Forward the request to the backend
    const response = await fetch(`${BACKEND_URL}/transcribe`, {
      method: 'POST',
      headers: {
        'Content-Type': req.headers['content-type'],
      },
      body: body,
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Backend error:', errorText);
      return res.status(response.status).json({ error: 'Transcription failed', details: errorText });
    }

    const data = await response.json();
    return res.status(200).json(data);
  } catch (error) {
    console.error('Proxy error:', error);
    return res.status(500).json({ error: 'Internal server error', message: error.message });
  }
}

module.exports = handler;
module.exports.config = {
  api: {
    bodyParser: false, // Disable body parsing to handle FormData
  },
};
