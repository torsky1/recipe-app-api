# Recipe App API

This repository contains a Recipe App API built using Django and Django REST Framework. The API provides functionality for managing recipes, ingredients, and tags, as well as user authentication and authorization. It is designed to be a backend service for a recipe management application.

## Features

- **User Authentication**: Secure user registration and login using JWT tokens.
- **Recipe Management**: Create, update, and delete recipes with various attributes.
- **Ingredient Management**: Add and manage ingredients associated with recipes.
- **Tagging**: Organize recipes using tags for easy searching and filtering.
- **Image Uploads**: Upload images for recipes.
- **Filter Recipes**: Filter recipes by tags and ingredients.
- **Pagination**: Paginated API responses for better performance with large datasets.

## Technologies Used

- **Django**: High-level Python web framework.
- **Django REST Framework**: Toolkit for building Web APIs.
- **PostgreSQL**: Database for storing data.
- **Docker**: Containerization for development and deployment.
- **GitHub Actions**: CI/CD for automated testing and deployment.

## Getting Started

### Prerequisites

- Docker and Docker Compose installed on your machine.

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/torsky1/recipe-app-api.git
   cd recipe-app-api

2. Apply database migrations:

   ```bash
   docker-compose run app sh -c "python manage.py makemigrations"
3. Create a superuser:

   ```bash
    docker-compose run app sh -c "python manage.py createsuperuser"

4. Build and run the Docker containers:

   ```bash
   docker-compose up
#  API Documentation
 - **Detailed API documentation is available at** http://localhost:8000/api/docs.

# Running Tests
 - To run tests, use the following command:
   ```bash
   docker-compose run --rm app sh -c "pytest"
   
#  Contributing
 - **Contributions are welcome!** Please fork the repository and submit a pull request with your changes.
