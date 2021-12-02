bash:
	docker exec -it djangoplicity-contacts bash

test:
	docker exec -it djangoplicity-contacts coverage run --source='.' manage.py test
	docker exec -it djangoplicity-contacts coverage html
	open ./htmlcov/index.html

coverage-html:
	docker exec -it djangoplicity-contacts coverage html
	open ./htmlcov/index.html

test-python27:
	docker exec -it djangoplicity-contacts tox -e py27-django111

create-user:
	docker exec -it djangoplicity-contacts ./manage.py createsuperuser

initial-fixture:
	docker exec -it djangoplicity-contacts ./manage.py loaddata initial
	docker exec -it djangoplicity-contacts ./manage.py loaddata countries
	docker exec -it djangoplicity-contacts ./manage.py update_regions
	docker exec -it djangoplicity-contacts ./manage.py loaddata actions
	docker exec -it djangoplicity-contacts ./manage.py loaddata imports
