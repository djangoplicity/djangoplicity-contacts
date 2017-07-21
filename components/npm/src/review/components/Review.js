import React, { Component } from 'react';

import { connect } from 'react-redux';

import {
	fetchImport,
} from '../actions';

import { Contact } from './Contact';


class Loading extends Component {
	render() {
		if (!this.props.ui.loading) {
			return false;
		}

		return <div>Loading...</div>;
	}
}

class Header extends Component {
	render() {
		return <thead>
			<tr>
				<th>Row</th>
				{this.props.fields.map((field, index) =>
					<th key={index}>{field[1]}</th>)}
			</tr>
		</thead>;
	}
}

class NewContacts extends Component {
	render() {
		if (this.props.newContacts.length === 0) {
			return false;
		}

		let newContacts = this.props.newContacts.map(
			(contact, index) => <Contact
				key={index}
				fields={contact}
				{...this.props}
			/>
		);

		return <div className="new-contacts">
			<h2>New contacts</h2>
			<table>
			<Header fields={this.props.contactFields} />
			<tbody>
				{newContacts}
			</tbody>
			</table>
		</div>;
	}
}

class Review extends Component {
	getCountry(pk) {
		return this.props.importData.countries.find(
			country => country.pk === pk);
	}

	getRegion(pk) {
		return this.props.importData.regions.find(
			region => region.pk === pk);
	}

	componentDidMount() {
		this.props.dispatch(fetchImport(importPK));
	}

	render() {
		return <div>
			<h1>Import review</h1>
			<Loading ui={this.props.ui} />
			<NewContacts
				newContacts={this.props.newContacts}
				contactFields={this.props.importData.contact_fields}
				getCountry={this.getCountry.bind(this)}
				getRegion={this.getRegion.bind(this)}
			/>
		</div>;
	}
}


function select(state) {
	return {
		importData: state.importData,
		newContacts: state.newContacts,
		ui: state.ui
	};
}

export default connect(select)(Review);
