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
  
  console.log(`[Proxy] ${method} ${url}`);
  
  try {
    const headers = new Headers();
    
    let body: any = undefined;
    
    // Handle different content types
    const contentType = request.headers.get('content-type');
    
    // Forward relevant headers, excluding problematic ones
    request.headers.forEach((value, key) => {
      const lowerKey = key.toLowerCase();
      if (!['host', 'connection', 'transfer-encoding', 'content-length'].includes(lowerKey)) {
        // For FormData, exclude content-type to let fetch set it with correct boundary
        if (lowerKey === 'content-type' && contentType?.includes('multipart/form-data')) {
          // Skip - let fetch handle FormData content-type with boundary
          return;
        }
        headers.set(key, value);
      }
    });
    
    // Debug: Log authorization header
    const authHeader = request.headers.get('authorization');
    console.log(`[Proxy Debug] Authorization header: ${authHeader ? 'Present' : 'Missing'}`);
    if (authHeader) {
      console.log(`[Proxy Debug] Auth header starts with: ${authHeader.substring(0, 20)}...`);
    }
    
    if (method !== 'GET' && method !== 'HEAD') {
      if (contentType?.includes('multipart/form-data')) {
        // Handle file uploads - let fetch handle the boundary
        body = await request.formData();
        console.log(`[Proxy Debug] Processing FormData, letting fetch set content-type boundary`);
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
    
    console.log(`[Proxy Response] ${method} ${url}: ${response.status} ${response.statusText}`);
    
    // Debug: Log error response body for 4xx errors
    if (response.status >= 400 && response.status < 500) {
      try {
        const responseClone = response.clone();
        const errorText = await responseClone.text();
        console.log(`[Proxy Debug] Error response body:`, errorText);
      } catch (e) {
        console.log(`[Proxy Debug] Could not read error response body`);
      }
    }
    
    // Handle different response types
    const responseContentType = response.headers.get('content-type');
    const contentDisposition = response.headers.get('content-disposition');
    
    // Check if this is a file download (has Content-Disposition: attachment)
    const isFileDownload = contentDisposition?.includes('attachment');
    
    if (responseContentType?.includes('application/json') && !isFileDownload) {
      const data = await response.json();
      return NextResponse.json(data, { 
        status: response.status,
        headers: {
          'Content-Type': 'application/json',
        }
      });
    } else if (responseContentType?.includes('text/') && !isFileDownload) {
      const text = await response.text();
      return new NextResponse(text, { 
        status: response.status,
        headers: {
          'Content-Type': responseContentType,
        }
      });
    } else {
      // Handle binary data (files, etc.) and file downloads
      const blob = await response.blob();
      const responseHeaders = new Headers({
        'Content-Type': responseContentType || 'application/octet-stream',
      });
      
      // Forward Content-Disposition header for file downloads
      if (contentDisposition) {
        responseHeaders.set('Content-Disposition', contentDisposition);
      }
      
      return new NextResponse(blob, { 
        status: response.status,
        headers: responseHeaders,
      });
    }
  } catch (error) {
    console.error(`[Proxy Error] ${method} ${url}:`, error);
    return NextResponse.json(
      { error: 'Internal proxy error', details: error instanceof Error ? error.message : String(error), url },
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