const express = require('express');

const app = express();
const PORT = 3000;
const OPA_URL =
	process.env.OPA_URL || 'http://opa:8181/v1/data/restaurant/authz/allow';

// This is the middleware that asks OPA for a decision
const checkAuth = async (req, res, next) => {
	const userRole = req.headers['x-user-role'] || 'guest';
	console.log(`Checking auth for role: ${userRole}, path: ${req.path}`);

	const input = {
		user: { role: userRole },
		path: req.path,
		method: req.method,
	};

	try {
		const controller = new AbortController();
		const timeout = setTimeout(() => controller.abort(), 5000);

		const response = await fetch(OPA_URL, {
			method: 'POST',
			body: JSON.stringify({ input }),
			headers: { 'Content-Type': 'application/json' },
			signal: controller.signal,
		});

		clearTimeout(timeout);

		if (!response.ok) {
			const errorText = await response.text();
			console.error(`OPA returned an error (${response.status}): ${errorText}`);
			return res.status(500).send(`Error from OPA: ${response.statusText}`);
		}

		const decision = await response.json();

		if (!decision.result) {
			console.log('Decision: DENY');
			return res.status(403).send('Access Denied');
		}

		console.log('Decision: ALLOW');
		next();
	} catch (error) {
		console.error('OPA Network Error:', error);
		res
			.status(500)
			.send('Error checking authorization: Could not connect to OPA.');
	}
};

app.use(checkAuth);

app.get('/menu', (req, res) => {
	res.json({
		starters: ['Salad', 'Soup'],
		mains: ['Burger', 'Pizza'],
	});
});

app.get('/payments', (req, res) => {
	res.json({
		total_revenue: 150000,
		currency: 'INR',
	});
});

app.listen(PORT, () => {
	console.log(`Restaurant API listening on port ${PORT}`);
});
