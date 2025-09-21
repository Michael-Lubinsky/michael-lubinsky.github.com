## Monad

<https://tech.nextroll.com/blog/dev/2022/11/11/exploring-monads-javascript.html>
```
One way to understand a monad is that it's essentially a container type with "map" and "flatten" operations. Let's say your monad is type M<T>.
The "map" operation allows you to take a function T->U and a container M<T>, and transform each element, giving you a container M<U>.
"Flatten" takes a container of type M<M<T>> and returns a container of type M<T>. So a List<List<Int>> becomes a List<Int>.

Now comes the trick: combine "map" and "flatten" to get "flatMap". So if you have a M<T> and a function T->M<U>, 
you use "map" to get an M<M<U>> and "flatten" to get an M<U>.

So why is this useful? Well, it lets you run computations which return all their values wrapped in weird "container" types. 
For example, if "M" is "Promise", then you can take a Promise<T> and an async function T->Promise<U>, and use flatMap to get a Promise<U>.

M could also be "Result", which gets you Rust-style error handling, or "Optional", which allows you to represent computations that might fail at each step (like in languages that support things like "value?.a?.b?.c"),
or a list (which gets you a language where each function returns many different possible results, so basically Python list comprehensions),
 or a whole bunch of other things.

So: Monads are basically any kind of weird container that supports "flatMap",
and they allow you to support a whole family of things that look like "Promise<T>" and async functions, all using the same framework.

Should you need to know this in most production code? Probably not! But if you're trying to implement something fancy that "works a bit like promises, or a bit like Python comprehensions, or maybe a bit like Rust error handling", then "weird containers with flatMap" is a very powerful starting point.

(Actual monads technically need a bit more than just flatMap, including the ability to turn a basic T into a Promise<T>,
and a bunch of consistency rules.)
```
