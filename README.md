# Catalog Application

Catalog App is a web application that provides a list of items within a variety of categories. It integrates with third party providers for authentication and user registration. Currently this project supports sign-in using either Google or Facebook accounts. Once signed in, users will have the ability to Add, Edit and Delete their own items.

### Prerequisites

Users would need to have an account with either `Google` or `Facebook` in order to sign in to this application.


### Setup

The following steps needs to be completed before running the application for the first time:

1. Install Vagrant and VirtualBox.

2. Clone the repository to `fullstack-nanodegree-vm-repository/vagrant/catalog`.

3. Launch the Vagrant VM (by typing `vagrant up` in the directory `fullstack-nanodegree-vm-repository/vagrant`)

4. Navigate to directory `fullstack-nanodegree-vm-repository/vagrant/catalog` to get started.

5. Setup the database

* Catalog App uses an sqllite database.
Execute `database_setup.py` to create and initialize the database.

```
python database_setup.py
```

* Load initial data (Optional)
Execute `insert_data.py` to populate the database with categories and items.

```
python insert_data.py
```

### Usage

1. To launch the Catalog App within the VM, run the file `catalogApp.py`

```
python catalogApp.py
```

2. Access the catalog App by visiting [http://localhost:5000](http://localhost:5000) locally on your browser.


### API Endpoints

The following APIs are provided for applications to consume data in JSON format: 

1. JSON API to fetch all Items in a Category 
`http://localhost:5000/category/<CATEGORY_NAME>/items/JSON`
Example:
[http://localhost:5000/category/Soccer/items/JSON](http://localhost:5000/category/Soccer/items/JSON)


2. JSON API to fetch information (name and description) about an item under a category
`http://localhost:5000/category/<CATEGORY_NAME>/item/<ITEM_NAME>/JSON`
Example:
[http://localhost:5000/category/Soccer/item/Jersey/JSON](http://localhost:5000/category/Soccer/item/Jersey/JSON)

3. JSON API to fetch all Categories
`http://localhost:5000/category/JSON`
Example:
[http://localhost:5000/category/JSON](http://localhost:5000/category/JSON)



