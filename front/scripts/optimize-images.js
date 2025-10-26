#!/usr/bin/env node

/**
 * Image optimization script to reduce bundle size
 * Converts and compresses images for web delivery
 */

const imagemin = require('imagemin');
const imageminMozjpeg = require('imagemin-mozjpeg');
const imageminPngquant = require('imagemin-pngquant');
const imageminWebp = require('imagemin-webp');
const fs = require('fs');
const path = require('path');

const ASSETS_DIR = path.join(__dirname, '../src/assets');
const OUTPUT_DIR = path.join(__dirname, '../src/assets/optimized');

async function optimizeImages() {
  console.log('🖼️  Starting image optimization...');

  // Ensure output directory exists
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  try {
    // Optimize JPEG images
    const jpegFiles = await imagemin([`${ASSETS_DIR}/*.{jpg,jpeg}`], {
      destination: OUTPUT_DIR,
      plugins: [
        imageminMozjpeg({
          quality: 85,
          progressive: true
        })
      ]
    });

    // Optimize PNG images
    const pngFiles = await imagemin([`${ASSETS_DIR}/*.png`], {
      destination: OUTPUT_DIR,
      plugins: [
        imageminPngquant({
          quality: [0.6, 0.8]
        })
      ]
    });

    // Generate WebP versions
    const webpFiles = await imagemin([`${ASSETS_DIR}/*.{jpg,jpeg,png}`], {
      destination: OUTPUT_DIR,
      plugins: [
        imageminWebp({
          quality: 80
        })
      ]
    });

    console.log('✅ Image optimization complete!');
    console.log(`📊 Optimized ${jpegFiles.length} JPEG files`);
    console.log(`📊 Optimized ${pngFiles.length} PNG files`);
    console.log(`📊 Generated ${webpFiles.length} WebP files`);

    // Calculate savings
    let originalSize = 0;
    let optimizedSize = 0;

    [...jpegFiles, ...pngFiles, ...webpFiles].forEach(file => {
      const originalPath = file.sourcePath;
      const optimizedPath = file.destinationPath;
      
      if (fs.existsSync(originalPath) && fs.existsSync(optimizedPath)) {
        originalSize += fs.statSync(originalPath).size;
        optimizedSize += fs.statSync(optimizedPath).size;
      }
    });

    const savings = ((originalSize - optimizedSize) / originalSize * 100).toFixed(1);
    console.log(`💾 Size reduction: ${savings}%`);
    console.log(`📦 Original: ${(originalSize / 1024 / 1024).toFixed(2)} MB`);
    console.log(`📦 Optimized: ${(optimizedSize / 1024 / 1024).toFixed(2)} MB`);

  } catch (error) {
    console.error('❌ Image optimization failed:', error);
    process.exit(1);
  }
}

// Run optimization
optimizeImages();
