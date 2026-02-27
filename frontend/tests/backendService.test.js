import { describe, it, expect } from 'vitest';
import { backendService } from '../backendService.ts';

describe('Backend Service Integration', () => {
  it('should test basic connectivity', async () => {
    console.log('Testing basic connectivity...');
    
    try {
      const testMessage = 'EXTRACTOR: Test message';
      const response = await backendService.callChatEndpoint(testMessage);
      
      expect(response).toBeDefined();
      console.log('✅ Backend connection successful');
      console.log('Response:', response);
    } catch (error) {
      console.error('❌ Test failed:', error.message);
      throw error;
    }
  });

  it('should have session management', () => {
    console.log('Testing session management...');
    expect(backendService.sessionId).toBeDefined();
    console.log('Session ID:', backendService.sessionId);
  });
});

// Keep the original function for backward compatibility
async function testBackendService() {
  console.log('Testing Backend Service Integration...');
  
  try {
    // Test 1: Basic connectivity
    console.log('\n1. Testing basic connectivity...');
    const testMessage = 'EXTRACTOR: Test message';
    const response = await backendService.callChatEndpoint(testMessage);
    console.log('✅ Backend connection successful');
    console.log('Response:', response);
    
    // Test 2: Session management
    console.log('\n2. Testing session management...');
    console.log('Session ID:', backendService.sessionId);
    
    console.log('\n✅ All tests passed!');
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
    console.error('Make sure the backend is running on http://localhost:8080');
  }
}

export { testBackendService };
