# TriTime

A timeclock app intended for FRC teams.

![image](https://github.com/user-attachments/assets/392d3b41-88d3-40d3-8917-6a61930a9216)


# Overview

Standalone app that can store data locally or use an Azure CosmosDB for
storage.

The idea being a very simple time tracking app suitable for FRC teams built on technology that's simple, easy, and useful. With that I've chosen Python for the language and wxWidgets for the GUI toolkit. I find wx especially pleasing to work with because it renders as a native app on whatever platform you're on, so if a student is working in Windows their app is a Windows app. If they're on macOS it's a macOS app. It also operates in a fairly straight forward manner.

In standalone version it uses local JSON files to store users and their time tracked results.

If fed the appropraite environment variables it will also hook up to an Azure CosmosDB and use JSON documents there to store the same data. This is a work in progress that needs to be documented further.