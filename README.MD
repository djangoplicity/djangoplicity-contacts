# Djangoplicity-contacts

Djangoplicity + Django 2.7 + Postgres 10.5

## Documentation ##

### How to install the template ###

Clone the repository, and update your origin url: 
```
git clone https://github.com/djangoplicity/djangoplicity-contacts.git
cd djangoplicity-contacts
```

### How to run the test project ###

The project use docker, so just run:

```
docker-compose up
```

> If it's first time, the images will be created. Sometimes the project doesn't run at first time because the init of postgres, just run again `docker-compose up` and it will work.

*Your app will run in url `localhost:8001`*

To recreate the docker images after dependencies changes run:

```
docker-compose up --build
```

To remove the docker containers including the database (Useful sometimes when dealing with migrations):

```
docker-compose down
```

### Make commands

The make command invokes the execution of the makefile. It is a special file that contains the shell commands that we create to maintain the project. The makefile contains targets and commands for execution.

Load initial data

```
make initial-fixture
```
*This runs inside the container the command ```./manage.py loaddata countries```*

Get country regions from [geonames.org](https://www.geonames.org/)
```
make load-regions
```
*This runs inside the container the command ```./manage.py update_regions```*
