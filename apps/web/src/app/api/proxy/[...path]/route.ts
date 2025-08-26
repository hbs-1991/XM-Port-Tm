import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = 'http://localhost:8000';

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join('/');
  const url = `${API_BASE_URL}/${path}`;
  
  const response = await fetch(url, {
    headers: Object.fromEntries(request.headers.entries()),
  });
  
  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}

export async function POST(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join('/');
  const url = `${API_BASE_URL}/${path}`;
  
  const body = await request.json();
  
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...Object.fromEntries(request.headers.entries()),
    },
    body: JSON.stringify(body),
  });
  
  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}

export async function OPTIONS(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return new NextResponse(null, { status: 200 });
}