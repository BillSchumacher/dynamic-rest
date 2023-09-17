# Created by billschumacher at 9/16/2023
Feature: Dynamic Model Serializer
  # Enter feature description here

    Scenario: Create endpoint should return errors when passing a bad request
    referencing a non-existent related model record.
      Given a "Country" model is available
        And a "Car" model is available
        And request data is available
        And the request has "name" with "Tesla"
        And the request has "country" with 42
        When I make an API "POST" request to "/cars" with data
        Then status code "400" is returned
        And values exist in the response
        | country |
        | "Invalid value for \'country\': Country object with ID=42 not found" |
