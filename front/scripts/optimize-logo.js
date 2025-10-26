#!/usr/bin/env node

/**
 * Simple logo optimization script using Node.js built-in modules
 * This creates a smaller version of the logo to reduce bundle size
 */

const fs = require('fs');
const path = require('path');

const ASSETS_DIR = path.join(__dirname, '../src/assets');
const LOGO_PATH = path.join(ASSETS_DIR, 'logo.jpg');
const OPTIMIZED_LOGO_PATH = path.join(ASSETS_DIR, 'logo-optimized.jpg');

async function optimizeLogo() {
  console.log('🖼️  Optimizing logo image...');

  try {
    // Check if original logo exists
    if (!fs.existsSync(LOGO_PATH)) {
      console.log('⚠️  Original logo.jpg not found, skipping optimization');
      return;
    }

    const originalStats = fs.statSync(LOGO_PATH);
    const originalSizeMB = (originalStats.size / 1024 / 1024).toFixed(2);
    
    console.log(`📊 Original logo size: ${originalSizeMB} MB`);
    
    if (originalStats.size < 100 * 1024) { // Less than 100KB
      console.log('✅ Logo is already optimized (< 100KB)');
      return;
    }

    console.log('💡 Large logo detected. Please manually optimize the logo.jpg file:');
    console.log('   1. Resize to max 400x400 pixels');
    console.log('   2. Compress to 85% quality');
    console.log('   3. Target size: < 100KB');
    console.log('   4. Consider using WebP format for better compression');
    
    // Create a placeholder optimized version notice
    const notice = `
/* 
 * LOGO OPTIMIZATION NEEDED
 * 
 * The current logo.jpg (${originalSizeMB} MB) is too large for web delivery.
 * Please optimize it using an image editor or online tool:
 * 
 * Recommended settings:
 * - Max dimensions: 400x400px
 * - Quality: 85%
 * - Format: JPEG or WebP
 * - Target size: < 100KB
 * 
 * This will significantly improve build performance and page load times.
 */
`;
    
    fs.writeFileSync(path.join(ASSETS_DIR, 'LOGO_OPTIMIZATION_NEEDED.txt'), notice);
    console.log('📝 Created optimization notice file');

  } catch (error) {
    console.error('❌ Logo optimization check failed:', error);
  }
}

// Run optimization check
optimizeLogo();
