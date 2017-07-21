// Actions types

export const RECEIVE_IMPORT = 'RECEIVE_IMPORT';
export const REQUEST_IMPORT = 'REQUEST_IMPORT';


function receiveImport(json) {
	return {
		type: RECEIVE_IMPORT,
		json
	};
}

function requestImport() {
	return {
		type: REQUEST_IMPORT
	};
}


// Async actions

export function fetchImport(pk) {
	return dispatch => {
		dispatch(requestImport());

		return fetch('/public/contacts/api/imports/' + pk + '/').then(
			response => response.json()
		).then(
			json => dispatch(receiveImport(json))
		);
	};
}
