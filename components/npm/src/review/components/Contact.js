import React, { Component } from 'react';


class CountryField extends Component {
	render() {
		let country = this.props.getCountry(this.props.value);
		return <span>{country.name}</span>;
	}
}

class RegionField extends Component {
	render() {
		let region = this.props.getRegion(this.props.value);
		return <span>{region.name}</span>;
	}
}

class TextField extends Component {
	render() {
		return <span>{this.props.value}</span>;
	}
}

class Field extends Component {
	render() {
		let field = false;

		switch (this.props.field) {
			case 'country':
				field = <CountryField {...this.props} />;
				break;

			default:
				field = <TextField {...this.props} />;
				break;
		}

		return <td>
			{field}
		</td>;
	}
}

export class Contact extends Component {
	getField(key, field, name) {
		return <Field
			key={key}
			field={field}
			name={name}
			value={this.props.fields[field]}
			{...this.props}
		/>;
	}

	render() {
		let fields = this.props.contactFields.map((field, index) =>
			this.getField(index + 1, field[0], field[1]));

		return <tr>
			{this.getField(0, 'row', 'Row')}
			{fields}
		</tr>;
	}
}
