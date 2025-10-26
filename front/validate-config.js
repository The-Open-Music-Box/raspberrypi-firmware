#!/usr/bin/env node

/**
 * Webpack configuration validation script
 * Tests the vue.config.js for syntax errors and configuration issues
 */

const fs = require('fs');
const path = require('path');

function validateConfig() {
  console.log('🔍 Validating webpack configuration...');

  try {
    // Test if vue.config.js can be loaded without errors
    const configPath = path.join(__dirname, 'vue.config.js');

    if (!fs.existsSync(configPath)) {
      throw new Error('vue.config.js not found');
    }

    // Try to require the config (this will catch syntax errors)
    delete require.cache[require.resolve('./vue.config.js')];
    const config = require('./vue.config.js');

    console.log('✅ Configuration syntax is valid');

    // Check key optimization features
    const checks = [
      {
        name: 'Code splitting configuration',
        test: () => config.configureWebpack && config.configureWebpack.optimization && config.configureWebpack.optimization.splitChunks
      },
      {
        name: 'Performance budgets',
        test: () => config.configureWebpack && config.configureWebpack.performance
      },
      {
        name: 'Chain webpack function',
        test: () => typeof config.chainWebpack === 'function'
      },
      {
        name: 'Alias configuration',
        test: () => config.configureWebpack && config.configureWebpack.resolve && config.configureWebpack.resolve.alias
      }
    ];

    let passed = 0;
    checks.forEach(check => {
      try {
        if (check.test()) {
          console.log(`✅ ${check.name}`);
          passed++;
        } else {
          console.log(`❌ ${check.name}`);
        }
      } catch (error) {
        console.log(`❌ ${check.name}: ${error.message}`);
      }
    });

    console.log(`\n📊 Configuration validation: ${passed}/${checks.length} checks passed`);

    if (passed === checks.length) {
      console.log('🎉 All optimizations are properly configured!');
      return true;
    } else {
      console.log('⚠️️  Some optimizations may not be working correctly');
      return false;
    }

  } catch (error) {
    console.error('❌ Configuration validation failed:', error.message);
    return false;
  }
}

// Run validation
const isValid = validateConfig();
process.exit(isValid ? 0 : 1);
