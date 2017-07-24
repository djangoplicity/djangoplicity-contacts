export function dataToNewContacts(importData) {
	// Extract the new contacts from the import (i.e.: contacts for which
	// we don't have duplicates

	let newContacts = importData.data.rows.filter(
	    (row) => !(row[0] in importData.duplicate_contacts)
	).map(row => {
		let contact = {
			row: row[0]
		};

		// Convert row to an object, including fields not in the import
		for (let field of importData.contact_fields) {
			let fieldIndex = importData.data.mapping.findIndex(
				mapping => mapping.field === field[0]
			);

			if (fieldIndex !== -1) {
				contact[field[0]] = row[fieldIndex + 1];
			} else {
				contact[field[0]] = null;
			}
		}

		return contact;
	});

	return newContacts;
}

export function updateContact(action, newContacts) {
	// Update the field given in action
	let index = newContacts.findIndex(contact => contact.row === action.row);

	return [
		...newContacts.slice(0, index),
		Object.assign({}, newContacts[index], {
			[action.field]: action.data
		}),
		...newContacts.slice(index + 1)
	];
}
