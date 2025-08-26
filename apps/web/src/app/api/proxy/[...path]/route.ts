import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function handleRequest(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
  method: string
) {
  const resolvedParams = await params;
  const path = resolvedParams.path.join('/');
  const url = `${API_BASE_URL}/${path}`;
  
  try {
    const headers = new Headers();
    
    // Forward relevant headers, excluding host-related ones
    request.headers.forEach((value, key) => {
      if (!['host', 'connection', 'transfer-encoding'].includes(key.toLowerCase())) {
        headers.set(key, value);
      }
    });
    
    let body: any = undefined;
    
    // Handle different content types
    const contentType = request.headers.get('content-type');
    if (method !== 'GET' && method !== 'HEAD') {
      if (contentType?.includes('multipart/form-data')) {
        // Handle file uploads
        body = await request.formData();
      } else if (contentType?.includes('application/json')) {
        body = await request.text(); // Keep as string to preserve formatting
      } else {
        body = await request.text();
      }
    }
    
    const response = await fetch(url, {
      method,
      headers,
      body: body instanceof FormData ? body : body,
    });
    
    // Handle different response types
    const responseContentType = response.headers.get('content-type');
    if (responseContentType?.includes('application/json')) {
      const data = await response.json();
      return NextResponse.json(data, { 
        status: response.status,
        headers: {
          'Content-Type': 'application/json',
        }
      });
    } else if (responseContentType?.includes('text/')) {
      const text = await response.text();
      return new NextResponse(text, { 
        status: response.status,
        headers: {
          'Content-Type': responseContentType,
        }
      });
    } else {
      // Handle binary data (files, etc.)
      const blob = await response.blob();
      return new NextResponse(blob, { 
        status: response.status,
        headers: {
          'Content-Type': responseContentType || 'application/octet-stream',
        }
      });
    }
  } catch (error) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      { error: 'Internal proxy error', details: error instanceof Error ? error.message : String(error) },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return handleRequest(request, context, 'GET');
}

export async function POST(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return handleRequest(request, context, 'POST');
}

export async function PUT(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return handleRequest(request, context, 'PUT');
}

export async function DELETE(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return handleRequest(request, context, 'DELETE');
}

export async function PATCH(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return handleRequest(request, context, 'PATCH');
}

export async function OPTIONS(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const resolvedParams = await params;
  return new NextResponse(null, { 
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS',
      'Access-Control-Allow-Headers': '*',
    }
  });
}