module.exports = {
	entry: {
		review: './src/review',
	},
	output: {
		path : __dirname + '/../../src/djangoplicity/contacts/static/js',
		filename: '[name].js'
	},
	devtool: 'inline-source-map',
	module: {
		loaders: [{
			test: /.jsx?$/,
			loader: 'babel-loader',
			exclude: /node_modules/,
			query: {
				presets: ['es2015', 'react']
			}
		}]
	},
};
