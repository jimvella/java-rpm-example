package au.id.jamesvella.myservice;

import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Created by Jim on 8/05/2015.
 */
@RestController
public class HelloController {

    @RequestMapping("/")
    public String helloWorld(){
        return "Hello rpm!";
    }
}
