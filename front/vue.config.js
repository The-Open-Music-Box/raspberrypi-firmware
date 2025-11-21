const { defineConfig } = require('@vue/cli-service');
const webpack = require('webpack');
const path = require('path');

module.exports = defineConfig({
  transpileDependencies: [],
  outputDir: process.env.VUE_APP_OUTPUT_DIR,
  publicPath: process.env.VUE_APP_PUBLIC_PATH,
  assetsDir: process.env.VUE_APP_ASSETS_DIR,

  devServer: {
    proxy: {
      '^/api': {
        target: process.env.VUE_APP_API_URL,
        changeOrigin: true,
        ws: false,
        logLevel: 'debug',
        onError: (err) => {
          console.log('Proxy Error:', err);
        },
        onProxyReq: (proxyReq, req) => {
          console.log('Proxying:', req.method, req.url, '→', proxyReq.path);
        }
      }
    },
  },

  configureWebpack: {
    plugins: [
      new webpack.DefinePlugin({
        __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: JSON.stringify(true),
      }),
    ],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src/'),
        '@components': path.resolve(__dirname, 'src/components/'),
        '@services': path.resolve(__dirname, 'src/services/'),
        '@i18n': path.resolve(__dirname, 'src/i18n/'),
        '@assets': path.resolve(__dirname, 'src/assets/'),
        '@views': path.resolve(__dirname, 'src/views/'),
        '@theme': path.resolve(__dirname, 'src/theme/'),
      }
    },
    optimization: {
      splitChunks: {
        chunks: 'all',
        cacheGroups: {
          // Separate Vue ecosystem libraries
          vue: {
            test: /[\\/]node_modules[\\/](vue|@vue|vue-router|pinia)[\\/]/,
            name: 'vue-vendor',
            priority: 20,
            chunks: 'all',
          },
          // UI libraries chunk
          ui: {
            test: /[\\/]node_modules[\\/](@headlessui|@heroicons)[\\/]/,
            name: 'ui-vendor',
            priority: 15,
            chunks: 'all',
          },
          // Socket.IO and communication
          socket: {
            test: /[\\/]node_modules[\\/](socket\.io-client|axios)[\\/]/,
            name: 'socket-vendor',
            priority: 15,
            chunks: 'all',
          },
          // FontAwesome icons (if used)
          icons: {
            test: /[\\/]node_modules[\\/](@fortawesome)[\\/]/,
            name: 'icons-vendor',
            priority: 15,
            chunks: 'all',
          },
          // Default vendor chunk for remaining dependencies
          vendor: {
            test: /[\\/]node_modules[\\/]/,
            name: 'vendor',
            priority: 10,
            chunks: 'all',
            minChunks: 2,
          },
          // Common application code
          common: {
            name: 'common',
            minChunks: 2,
            priority: 5,
            chunks: 'all',
            enforce: true,
          },
        },
      },
      // Enable runtime chunk for better caching
      runtimeChunk: {
        name: 'runtime',
      },
    },
    performance: {
      // Increase limits but keep them reasonable
      maxAssetSize: 300000, // 300KB
      maxEntrypointSize: 300000, // 300KB
      hints: 'warning',
    },
  },

  chainWebpack: (config) => {
    // Image optimization (simplified to avoid loader issues)
    // Note: Using default Vue CLI image handling

    // Enable gzip compression for production (optional)
    if (process.env.NODE_ENV === 'production') {
      try {
        const CompressionWebpackPlugin = require('compression-webpack-plugin');
        config
          .plugin('CompressionWebpackPlugin')
          .use(CompressionWebpackPlugin, [
            {
              algorithm: 'gzip',
              test: /\.(js|css|html|svg)$/,
              threshold: 8192,
              minRatio: 0.8,
            },
          ]);
      } catch (error) {
        console.warn('⚠️️  compression-webpack-plugin not found, skipping gzip compression');
      }
    }

    // Note: Preload and prefetch plugin configuration removed to avoid build errors
    // These optimizations can be added later if needed
  },
});